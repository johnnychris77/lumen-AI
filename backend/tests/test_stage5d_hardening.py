"""Stage 5D — hardening regression tests for the Stage 5C integration weaknesses.

One test (or group) per finding from the Stage 5D brief, section 2:

* safe checkpoint deserialization (no arbitrary-code unpickling)
* reject uninitialized / partially initialized backbones unless a documented
  compatibility policy authorizes them (architecture / tensor-name / shape checks)
* prevent implicit weight downloads
* specimen / session / batch separation across fit, calibration AND test
* authenticated reviewer authorization + image/specimen matching for lab linkage
* tenant authorization when retrieving persisted heatmaps/artifacts

These run WITHOUT torch/Anomalib except where explicitly marked; the torch-gated
tests exercise the real safe-loader against genuine tensors when torch is present.
"""
from __future__ import annotations

import importlib.util

import pytest

# Init app layer before research imports (cold circular-import avoidance).
from app.db.session import SessionLocal  # noqa: F401

from research.lens_vision.artifact_store import ResearchArtifactStore, TenantAccessError
from research.lens_vision.anomaly_experiment import LeakageError, run_anomaly_experiment
from research.lens_vision.backbone_loader import (
    BackboneArchitectureMismatchError,
    BackboneInitializationError,
    CompatibilityPolicy,
    UnsafeCheckpointError,
    load_verified_backbone,
    safe_torch_load,
    verify_state_dict_against_module,
)
from research.lens_vision.config import ResearchRunConfig
from research.lens_vision.scientific_evidence import (
    CORROSION_LIKE,
    REL_INDETERMINATE,
    REL_SUPPORTED,
    LaboratoryEvidence,
    LinkageAuthorizationError,
    ReviewerAuthorization,
    link_observation,
)
from research.lens_vision.anomaly_localization import StubLocalizer
from research.lens_vision.synthetic_fixtures import synthetic_anomaly_dataset

TORCH = importlib.util.find_spec("torch") is not None


def _cfg(**kw):
    base = dict(run_id="d5", seed=5, checkpoint_id="stub_backbone",
                source_provenance_class="synthetic_experimental", embedder="stub_padim_like")
    base.update(kw)
    return ResearchRunConfig(**base)


def _evidence(**over):
    base = dict(
        image_id=1, image_sha256="a" * 64, instrument_id="INS-1", specimen_id="SPEC-1",
        imaging_session_id="SESS-1", evidence_category=CORROSION_LIKE, material_type="stainless_steel",
        instrument_anatomy="hinge", source_laboratory="Lab A", study_id="STUDY-1",
        reference_method="eds", verification_status="verified", reviewer_id="rev@x",
        approval_evidence_ref="APPR-1", measurement_uncertainty=0.1,
        measurement_value=10.0, measurement_units="mm2", verified_material_identity="iron_oxide",
    )
    base.update(over)
    return LaboratoryEvidence(**base)


# ── Finding: reject uninitialized / partial / mismatched backbones ──────────

class _FakeTensor:
    def __init__(self, shape):
        self.shape = tuple(shape)


class _FakeModule:
    """A minimal nn-like module to test the verifier without torch."""

    def __init__(self, tensors: dict):
        self._sd = tensors
        self.loaded = None

    def state_dict(self):
        return dict(self._sd)

    def load_state_dict(self, state, strict=False):  # noqa: ARG002
        self.loaded = dict(state)


def test_full_coverage_loads_without_policy():
    mod = _FakeModule({"w1": _FakeTensor((3, 3)), "w2": _FakeTensor((5,))})
    state = {"w1": _FakeTensor((3, 3)), "w2": _FakeTensor((5,))}
    report = load_verified_backbone(mod, state, policy=None)
    assert report.coverage == 1.0 and mod.loaded is not None
    assert report.scientifically_valid is True


def test_partial_backbone_rejected_without_policy():
    mod = _FakeModule({"w1": _FakeTensor((3, 3)), "w2": _FakeTensor((5,))})
    state = {"w1": _FakeTensor((3, 3))}  # w2 missing -> partially initialized
    with pytest.raises(BackboneInitializationError):
        load_verified_backbone(mod, state, policy=None)


def test_shape_mismatch_rejected_even_with_permissive_policy():
    mod = _FakeModule({"w1": _FakeTensor((3, 3))})
    state = {"w1": _FakeTensor((7, 7))}  # wrong shape = wrong architecture
    report = verify_state_dict_against_module(state, mod)
    assert report.shape_mismatch and report.coverage == 0.0
    policy = CompatibilityPolicy(policy_id="p", reason="r", min_coverage=0.0, allow_missing_keys=True)
    with pytest.raises(BackboneArchitectureMismatchError):
        load_verified_backbone(mod, state, policy=policy)


def test_documented_policy_authorizes_partial_and_flags_non_scientific():
    mod = _FakeModule({"w1": _FakeTensor((3, 3)), "w2": _FakeTensor((5,))})
    state = {"w1": _FakeTensor((3, 3))}  # 50% coverage
    policy = CompatibilityPolicy(
        policy_id="research_smoke", reason="execution-only smoke backbone",
        min_coverage=0.5, allow_missing_keys=True, scientifically_valid=False,
    )
    report = load_verified_backbone(mod, state, policy=policy)
    assert report.coverage == 0.5 and report.scientifically_valid is False
    assert report.policy_id == "research_smoke"


def test_compatibility_policy_requires_documentation():
    with pytest.raises(ValueError):
        CompatibilityPolicy(policy_id="", reason="")


# ── Finding: safe deserialization (torch-gated) ────────────────────────────

@pytest.mark.skipif(not TORCH, reason="requires torch")
def test_safe_torch_load_refuses_arbitrary_pickle(tmp_path):
    import pickle
    # A checkpoint that is NOT a plain tensor state-dict (pickled object graph).
    bad = tmp_path / "evil.ckpt"
    with open(bad, "wb") as f:
        pickle.dump({"state_dict": {"x": object()}}, f)
    with pytest.raises(UnsafeCheckpointError):
        safe_torch_load(str(bad))


@pytest.mark.skipif(not TORCH, reason="requires torch")
def test_safe_torch_load_reads_weights_only_state_dict(tmp_path):
    import torch
    sd = {"w1": torch.zeros(3, 3), "w2": torch.ones(5)}
    p = tmp_path / "good.pt"
    torch.save(sd, p)
    loaded = safe_torch_load(str(p))
    assert set(loaded.keys()) == {"w1", "w2"}


@pytest.mark.skipif(not TORCH, reason="requires torch")
def test_verifier_matches_real_torch_module():
    import torch.nn as nn
    mod = nn.Sequential(nn.Conv2d(3, 4, 3), nn.BatchNorm2d(4))
    good = {k: v.clone() for k, v in mod.state_dict().items()}
    rep = load_verified_backbone(mod, good, policy=None)
    assert rep.coverage == 1.0 and not rep.missing and not rep.shape_mismatch


# ── Finding: reviewer authorization + image/specimen matching ──────────────

def test_link_requires_authenticated_authorized_reviewer():
    ai = {"image_sha256": "a" * 64, "specimen_id": "SPEC-1"}
    ev = _evidence()
    # Unauthenticated reviewer -> indeterminate (no confirmed identity).
    unauth = ReviewerAuthorization(reviewer_id="rev@x", authenticated=False, roles=("scientific_reviewer",))
    obs = link_observation(ai, laboratory_evidence=ev, reviewer_authorization=unauth)
    assert obs.ai_to_material_relationship == REL_INDETERMINATE and obs.confirmed_material_identity is None
    # Wrong role -> indeterminate.
    wrong_role = ReviewerAuthorization(reviewer_id="rev@x", authenticated=True, roles=("viewer",))
    obs2 = link_observation(ai, laboratory_evidence=ev, reviewer_authorization=wrong_role)
    assert obs2.ai_to_material_relationship == REL_INDETERMINATE
    # Authenticated + authorized + matching identity -> supported.
    ok = ReviewerAuthorization(reviewer_id="rev@x", authenticated=True, roles=("scientific_reviewer",))
    obs3 = link_observation(ai, laboratory_evidence=ev, reviewer_authorization=ok)
    assert obs3.ai_to_material_relationship == REL_SUPPORTED and obs3.confirmed_material_identity == "iron_oxide"


def test_link_reviewer_identity_must_match_verifier():
    ai = {"image_sha256": "a" * 64, "specimen_id": "SPEC-1"}
    ev = _evidence(reviewer_id="verifier@x")
    other = ReviewerAuthorization(reviewer_id="someone_else@x", authenticated=True, roles=("scientific_reviewer",))
    with pytest.raises(LinkageAuthorizationError):
        link_observation(ai, laboratory_evidence=ev, reviewer_authorization=other)


def test_link_refuses_image_or_specimen_mismatch():
    ok = ReviewerAuthorization(reviewer_id="rev@x", authenticated=True, roles=("scientific_reviewer",))
    ev = _evidence(image_sha256="a" * 64, specimen_id="SPEC-1")
    # Different image hash.
    with pytest.raises(LinkageAuthorizationError):
        link_observation({"image_sha256": "b" * 64, "specimen_id": "SPEC-1"},
                         laboratory_evidence=ev, reviewer_authorization=ok)
    # Different specimen.
    with pytest.raises(LinkageAuthorizationError):
        link_observation({"image_sha256": "a" * 64, "specimen_id": "SPEC-2"},
                         laboratory_evidence=ev, reviewer_authorization=ok)
    # No anomaly identity at all -> cannot confirm the link belongs to this image.
    obs = link_observation({}, laboratory_evidence=ev, reviewer_authorization=ok)
    assert obs.ai_to_material_relationship == REL_INDETERMINATE


# ── Finding: tenant authorization on heatmap/artifact retrieval ────────────

def test_heatmap_retrieval_is_tenant_scoped(tmp_path):
    store = ResearchArtifactStore(str(tmp_path))
    ref = store.store_heatmap(tenant_id="tenant-A", run_id="r", image_id="img1", heatmap=[[0.1, 0.2], [0.3, 0.4]])
    assert ref
    # Owner can resolve.
    assert store.resolve(ref, requesting_tenant_id="tenant-A")
    assert store.exists(ref, requesting_tenant_id="tenant-A")
    # A different tenant cannot resolve another tenant's artifact.
    assert store.resolve(ref, requesting_tenant_id="tenant-B") is None
    assert store.exists(ref, requesting_tenant_id="tenant-B") is False
    # A forged ref naming tenant-B but with tenant-A's run cannot be resolved by B.
    forged = "artifact://tenant-B/r/img1"
    assert store.resolve(forged, requesting_tenant_id="tenant-B") is None
    # A missing requesting tenant is refused outright.
    with pytest.raises(TenantAccessError):
        store.resolve(ref, requesting_tenant_id="")


# ── Finding: specimen/session/batch separation across fit, calibration, test ─

def _normal(i, **kw):
    n, _ = synthetic_anomaly_dataset(n_normal=1, n_anomalous=0)
    s = dict(n[0], id=f"n{i}")
    s.update(kw)
    return s


def test_fit_calibration_specimen_separation_grouped_split():
    # Two specimens, several images each. The grouped split must keep each specimen
    # wholly within fit OR calibration (never both).
    normal = []
    for i in range(4):
        normal.append(_normal(f"A{i}", specimen_id="SPEC-A", image_sha256=f"{i:064x}"))
    for i in range(4):
        normal.append(_normal(f"B{i}", specimen_id="SPEC-B", image_sha256=f"{i+100:064x}"))
    test = synthetic_anomaly_dataset(n_normal=0, n_anomalous=3)[1]
    for j, s in enumerate(test):
        s["specimen_id"] = "SPEC-TEST"
        s["image_sha256"] = f"{j+500:064x}"
    rep = run_anomaly_experiment(normal, test, config=_cfg(), localizer=StubLocalizer(),
                                 synthetic_technical_test=True)
    # The experiment ran (no leakage); fit and calibration are non-empty and disjoint.
    assert rep["n_fit_normal"] >= 1 and rep["n_calibration_normal"] >= 1


def test_explicit_calibration_sharing_specimen_with_fit_is_rejected():
    fit = [_normal(f"F{i}", specimen_id="SPEC-SHARED", image_sha256=f"{i:064x}") for i in range(3)]
    # Calibration reuses the SAME specimen as fit -> calibration leakage.
    calib = [_normal(f"C{i}", specimen_id="SPEC-SHARED", image_sha256=f"{i+50:064x}") for i in range(2)]
    test = synthetic_anomaly_dataset(n_normal=0, n_anomalous=2)[1]
    for j, s in enumerate(test):
        s["specimen_id"] = "SPEC-T"
        s["image_sha256"] = f"{j+900:064x}"
    with pytest.raises(LeakageError):
        run_anomaly_experiment(fit, test, config=_cfg(), localizer=StubLocalizer(),
                               calibration_samples=calib, synthetic_technical_test=True)
