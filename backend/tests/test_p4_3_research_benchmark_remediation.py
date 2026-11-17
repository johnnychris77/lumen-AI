"""P4.3 — research-benchmark integrity & governance remediation regression tests.

Each test reproduces a confirmed RGI finding and asserts the remediated behaviour. All
data is synthetic; no real images, no network, no ingestion. These tests fail against the
pre-P4.3 code and pass after the remediation.
"""
from __future__ import annotations

import pytest

# Init app layer before research imports (cold circular-import avoidance).
from app.db.session import SessionLocal  # noqa: F401

from research.lens_vision import checkpoint as ckpt
from research.lens_vision.anomaly_contract import AnomalyResult
from research.lens_vision.anomaly_experiment import (
    InvalidLabelError,
    LeakageError,
    LocalizerConfigMismatchError,
    run_anomaly_experiment,
)
from research.lens_vision.anomaly_feasibility import AnomalyRegion
from research.lens_vision.anomaly_localization import StubLocalizer
from research.lens_vision.artifact_store import ResearchArtifactStore, TenantAccessError
from research.lens_vision.calibration import average_precision
from research.lens_vision.cohort_readiness import (
    GT_VERIFIED_NORMAL,
    MODALITY_EXTERNAL,
    generate_cohort_readiness_report,
    valid_statistical_signoff,
    validate_image_readiness,
)
from research.lens_vision.config import ResearchRunConfig
from research.lens_vision.synthetic_fixtures import synthetic_anomaly_dataset


def _cfg(checkpoint_id="stub_backbone", **kw):
    base = dict(run_id="anom", seed=11, checkpoint_id=checkpoint_id,
                source_provenance_class="synthetic_experimental", embedder="stub_padim_like")
    base.update(kw)
    return ResearchRunConfig(**base)


def _img(**over):
    base = dict(
        image_id="img-1", image_sha256="a" * 64, instrument_id="INS-1", specimen_id="SPEC-1",
        modality=MODALITY_EXTERNAL, anatomy_zone="hinge", imaging_session_id="SESS-1",
        imaging_device="camA", data_provenance_class="external_nonclinical",
        institutional_authorization_ref="IRB-1", data_rights="research_use", retention_status="active",
        study_batch_id="BATCH-1", split="fit", ground_truth_status=GT_VERIFIED_NORMAL,
        label_reviewer_id="rev@x",
    )
    base.update(over)
    return base


# ── RGI-01: authorization value validation ───────────────────────────────────

def test_rgi01_denied_rights_and_purged_retention_fail_authorization():
    for field, bad in (("data_rights", "denied"), ("retention_status", "purged")):
        r = validate_image_readiness(_img(**{field: bad}))
        assert r["authorization_blockers"], f"{field}={bad} must fail authorization"
        assert r["ready"] is False
    # A fabricated-but-nonempty authorization value does not pass via mere presence.
    r = validate_image_readiness(_img(data_rights="totally-made-up"))
    assert any("data_rights_not_granted" in b for b in r["authorization_blockers"])
    # Legitimate granted/active values still pass.
    assert not validate_image_readiness(_img())["authorization_blockers"]


# ── RGI-02: scientific/statistical sign-off is affirmative, not truthy ────────

def test_rgi02_signoff_requires_affirmative_approval():
    assert valid_statistical_signoff({"approved": True, "reviewer_id": "stat@x"}) is True
    assert valid_statistical_signoff({"approved": False, "reviewer_id": "stat@x"}) is False
    assert valid_statistical_signoff({"rejected": True, "reviewer_id": "stat@x"}) is False
    assert valid_statistical_signoff({"approved": True, "revoked": True, "reviewer_id": "x"}) is False
    assert valid_statistical_signoff({"reviewer_id": "stat@x"}) is False          # bare id
    assert valid_statistical_signoff({"approved": True}) is False                 # no reviewer
    assert valid_statistical_signoff({}) is False and valid_statistical_signoff(None) is False


# ── RGI-03 / 168-f: execution-only checkpoint is never scientific ─────────────

def test_rgi03_execution_only_forces_non_scientific_policy(tmp_path):
    w = tmp_path / "rand.pt"
    w.write_bytes(b"random-weights")
    # Caller tries to claim scientifically_valid=True on an execution-only backbone.
    rec = ckpt.register_operator_approved_checkpoint(
        "p43_exec", file_path=str(w), architecture="resnet18", license="n/a", source_url="",
        description="exec", approver_id="op@x", research_execution_only=True,
        compatibility_policy={"policy_id": "p", "scientifically_valid": True})
    try:
        assert rec.scientific_use_approved is False
        # The stored policy is FORCED non-scientific so the localizer cannot derive validity.
        assert rec.compatibility_policy.get("scientifically_valid") is False
        with pytest.raises(ckpt.CheckpointScientificUseError):
            ckpt.assert_scientific_checkpoint(rec)
    finally:
        del ckpt._REGISTRY["p43_exec"]


def test_rgi03_metric_path_flags_and_can_refuse_non_scientific_checkpoint():
    normal, test = synthetic_anomaly_dataset(n_normal=6, n_anomalous=4)
    # Stub backbone is approved-for-execution but NOT scientific → metrics flagged technical.
    rep = run_anomaly_experiment(normal, test, config=_cfg(), localizer=StubLocalizer())
    assert rep["scientifically_eligible"] is False
    assert rep["scientific_metrics_published"] is False
    assert rep["image_level_metrics"]["scientific"] is False
    # A publisher that demands scientific eligibility is REFUSED in the metric path itself.
    with pytest.raises(ckpt.CheckpointScientificUseError):
        run_anomaly_experiment(normal, test, config=_cfg(), localizer=StubLocalizer(),
                               require_scientific=True)


# ── RGI-04: tenant-safe artifact store ───────────────────────────────────────

def test_rgi04_distinct_tenants_do_not_collide_or_overwrite(tmp_path):
    store = ResearchArtifactStore(str(tmp_path))
    hm = [[0.1, 0.2], [0.3, 0.4]]
    # "a/b" and "ab" previously collapsed to the same safe component → collision.
    ref1 = store.store_heatmap(tenant_id="a/b", run_id="r", image_id="img", heatmap=hm)
    ref2 = store.store_heatmap(tenant_id="ab", run_id="r", image_id="img", heatmap=[[9.0, 9.0], [9.0, 9.0]])
    assert ref1 and ref2 and ref1 != ref2
    # Each tenant resolves ONLY its own artifact; neither can read the other's.
    assert store.resolve(ref1, requesting_tenant_id="a/b")
    assert store.resolve(ref1, requesting_tenant_id="ab") is None
    assert store.resolve(ref2, requesting_tenant_id="ab")
    assert store.resolve(ref2, requesting_tenant_id="a/b") is None


def test_rgi04_path_traversal_and_crafted_refs_rejected(tmp_path):
    store = ResearchArtifactStore(str(tmp_path))
    hm = [[0.1, 0.2], [0.3, 0.4]]
    # A traversal attempt via identity components stays inside base_dir (hex-encoded).
    ref = store.store_heatmap(tenant_id="..", run_id="..", image_id="..", heatmap=hm)
    import os
    if ref:
        path = store.resolve(ref, requesting_tenant_id="..")
        assert path is None or os.path.abspath(path).startswith(store.base_dir + os.sep)
    # A crafted non-hex ref (e.g. containing '..') is rejected before touching the FS.
    assert store.resolve("artifact://../../etc/passwd", requesting_tenant_id="x") is None
    with pytest.raises(TenantAccessError):
        store.resolve(ref or "artifact://aa/bb/cc", requesting_tenant_id="")


# ── RGI-05: duplicate-image leakage from bytes ───────────────────────────────

def test_rgi05_identical_bytes_detected_as_leakage_despite_different_declared_hashes():
    normal, _ = synthetic_anomaly_dataset(n_normal=4, n_anomalous=0)
    dup_bytes = b"\x01\x02\x03identical-image-bytes-across-splits"

    def _clear(s, **over):
        s = dict(s)
        # Strip every physical identity EXCEPT the image bytes, so the ONLY thing that can
        # link two records is the byte-derived SHA — isolating the RGI-05 behaviour.
        s.update(instrument_serial="", inspection_id="", session_id="", specimen_id="",
                 laboratory_batch_id="")
        s.update(over)
        return s

    # Valid but DIFFERENT declared hashes (so governance passes), yet identical bytes.
    fit = [_clear(n, id=f"f{i}", image_sha256=f"{i:064d}") for i, n in enumerate(normal)]
    fit[0]["image_bytes"] = dup_bytes
    held = _clear(normal[0], id="held", image_sha256="f" * 64, image_bytes=dup_bytes)
    with pytest.raises(LeakageError):
        run_anomaly_experiment(fit, [held], config=_cfg(), localizer=StubLocalizer())


def test_rgi05_repeat_of_links_original_to_repeat_across_splits():
    manifest = [
        _img(image_id="ORIG", split="fit", specimen_id="S1", image_sha256="1" * 64),
        _img(image_id="REPEAT", split="validation", specimen_id="S2", image_sha256="2" * 64,
             repeat_of="ORIG"),
    ]
    rep = generate_cohort_readiness_report(manifest)
    assert any("repeat:ORIG" in x for x in rep["cross_split_leakage"])


# ── RGI-06: ground-truth readiness by split ──────────────────────────────────

def test_rgi06_unlabeled_fails_fit_and_sealed_test_without_intended_use():
    # Unlabeled fit image (no intended_use field) must fail ground-truth readiness.
    r_fit = validate_image_readiness(_img(split="fit", ground_truth_status="unlabeled",
                                          label_reviewer_id=""))
    assert any("fit_requires_verified_normal" in b for b in r_fit["ground_truth_blockers"])
    r_sealed = validate_image_readiness(_img(split="sealed_test", ground_truth_status="unlabeled",
                                             label_reviewer_id=""))
    assert any("sealed_test_requires_reviewed_label" in b for b in r_sealed["ground_truth_blockers"])


# ── RGI-07: independent readiness dimensions ─────────────────────────────────

def test_rgi07_missing_authorization_does_not_fail_metadata_dimension():
    r = validate_image_readiness(_img(institutional_authorization_ref="", data_rights="",
                                      retention_status=""))
    assert r["authorization_blockers"]
    # None of the three authorization fields appear as METADATA blockers.
    assert not any(b.startswith("missing:institutional_authorization_ref")
                   or b.startswith("missing:data_rights") or b.startswith("missing:retention_status")
                   for b in r["metadata_blockers"])


# ── RGI-08: localizer/config identity ────────────────────────────────────────

def test_rgi08_localizer_checkpoint_must_match_config():
    normal, test = synthetic_anomaly_dataset(n_normal=6, n_anomalous=4)
    loc = StubLocalizer()
    loc.checkpoint_id = "a-different-backbone"  # disagree with config's stub_backbone
    with pytest.raises(LocalizerConfigMismatchError):
        run_anomaly_experiment(normal, test, config=_cfg(checkpoint_id="stub_backbone"), localizer=loc)


# ── RGI-09: binary label validation ──────────────────────────────────────────

def test_rgi09_non_binary_labels_rejected():
    normal, test = synthetic_anomaly_dataset(n_normal=6, n_anomalous=4)
    bad = [dict(t) for t in test]
    bad[0]["anomaly_label"] = 2  # out of the binary domain
    with pytest.raises(InvalidLabelError):
        run_anomaly_experiment(normal, bad, config=_cfg(), localizer=StubLocalizer())


# ── RGI-11: deterministic average precision under ties ───────────────────────

def test_rgi11_average_precision_is_tie_order_independent():
    # The pre-fix per-item AP gave 1.0 vs 0.5 for these two identical-prediction cases.
    assert average_precision([0.5, 0.5], [1, 0]) == average_precision([0.5, 0.5], [0, 1])
    # Permuting the label assignment WITHIN a single tied score block cannot change AP,
    # because all equal-score items are scored as one group.
    assert (average_precision([0.9, 0.9, 0.9], [1, 0, 1])
            == average_precision([0.9, 0.9, 0.9], [0, 1, 1])
            == average_precision([0.9, 0.9, 0.9], [1, 1, 0]))


# ── RGI-13: research-only guarantees non-overridable ─────────────────────────

def test_rgi13_result_and_region_guarantees_cannot_be_overridden():
    with pytest.raises(TypeError):
        AnomalyResult(  # research_only is init=False now
            source_image_id="i", source_image_sha256="", provenance_class="", provenance_source_id="",
            tenant_id="t", model_architecture="", checkpoint_id="", checkpoint_digest="",
            research_run_id="r", run_version="v", image_level_anomaly_score=0.1, heatmap_ref="",
            heatmap_shape=(1, 1), research_only=False)
    with pytest.raises(TypeError):
        AnomalyRegion(x=0, y=0, width=1, height=1, anomaly_score=1.0, confirmed_diagnosis="rust")
