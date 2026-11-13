"""Explicit, verifiable checkpoint approval — never auto-download.

A research run may only load a checkpoint that is (a) listed in the approval
registry, (b) explicitly ``approved``, (c) has its data/usage ``rights_cleared``,
and (d) whose on-disk file content SHA-256 matches the registered digest. Weights
are never committed to the repository and are never downloaded automatically; an
operator places an approved checkpoint file on disk in an isolated research
environment and records its digest here.

The DINOv2 checkpoints are listed but ship **unapproved / rights-not-cleared**,
so the real embedding path is a documented, governed blocker until licensing and
data-rights are verified and approved (see the Stage 5A plan).
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass


class CheckpointError(RuntimeError):
    """Base class for checkpoint governance failures."""


class CheckpointNotRegisteredError(CheckpointError):
    pass


class CheckpointNotApprovedError(CheckpointError):
    pass


class CheckpointRightsError(CheckpointError):
    pass


class CheckpointFileMissingError(CheckpointError):
    pass


class CheckpointVerificationError(CheckpointError):
    pass


class CheckpointScientificUseError(CheckpointError):
    """A checkpoint not approved for scientific performance claims was used for one
    (e.g. a locally-generated random-weight backbone, or missing license evidence)."""


@dataclass(frozen=True)
class CheckpointRecord:
    checkpoint_id: str
    description: str
    license: str
    source_url: str
    expected_sha256: str      # digest of the on-disk file ("" => no file, e.g. the stub)
    approved: bool            # a human approved this checkpoint for research use
    rights_cleared: bool      # data/usage rights for this checkpoint are verified
    requires_file: bool       # whether a real weights file must be present + verified
    architecture: str = ""    # the architecture this checkpoint IS (compatibility check)
    # Checkpoint-specific preprocessing contract (resize + normalization), so a
    # run can never silently apply the wrong transform to the wrong weights.
    preprocessing: dict | None = None
    # Optional, explicit authorization to deviate from full, exact weight loading
    # (see backbone_loader.CompatibilityPolicy). None => the backbone must be
    # fully initialized from the checkpoint (every tensor, exact shapes). A policy
    # may set scientifically_valid=False (research-execution smoke only).
    compatibility_policy: dict | None = None
    # Stage 6B checkpoint-governance evidence (fail-closed). Rights clearance and
    # scientific use require an authenticated approver and verifiable license/source
    # evidence; a random-weight / research-execution backbone is never scientific.
    approver_id: str = ""
    license_evidence_ref: str = ""
    source_evidence_ref: str = ""
    scientific_use_approved: bool = False


# The approval registry. DINOv2 is listed but intentionally NOT approved and NOT
# rights-cleared: the real path is blocked until licensing/data-rights are
# verified. Only the deterministic smoke stub (no weights, no network) is approved
# — and it is explicitly NOT a scientific model.
_REGISTRY: dict[str, CheckpointRecord] = {
    "smoke_stub": CheckpointRecord(
        checkpoint_id="smoke_stub",
        description="Deterministic Pillow-based stub embedder for CPU pipeline smoke tests ONLY. "
                    "Not a learned model; produces no scientific embeddings.",
        license="n/a (internal stub)",
        source_url="",
        expected_sha256="",
        approved=True,
        rights_cleared=True,
        requires_file=False,
    ),
    "dinov2_vits14": CheckpointRecord(
        checkpoint_id="dinov2_vits14",
        description="DINOv2 ViT-S/14 frozen backbone (Meta).",
        license="Apache-2.0 (verify upstream before use)",
        source_url="https://github.com/facebookresearch/dinov2",
        expected_sha256="",  # operator records the real digest when approving
        approved=False,       # BLOCKED: awaiting license + data-rights verification
        rights_cleared=False,
        requires_file=True,
        architecture="vit_small_patch14_dinov2",
        preprocessing={
            "resize": [224, 224], "interpolation": "bicubic",
            "mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225],
        },
    ),
    "dinov2_vitb14": CheckpointRecord(
        checkpoint_id="dinov2_vitb14",
        description="DINOv2 ViT-B/14 frozen backbone (Meta).",
        license="Apache-2.0 (verify upstream before use)",
        source_url="https://github.com/facebookresearch/dinov2",
        expected_sha256="",
        approved=False,
        rights_cleared=False,
        requires_file=True,
        architecture="vit_base_patch14_dinov2",
        preprocessing={
            "resize": [224, 224], "interpolation": "bicubic",
            "mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225],
        },
    ),
    # Stage 5B anomaly-localization backbones (Anomalib PaDiM/PatchCore). Listed
    # but BLOCKED until license + data-rights are verified and a digest recorded.
    "resnet18_imagenet": CheckpointRecord(
        checkpoint_id="resnet18_imagenet",
        description="ResNet-18 ImageNet-pretrained backbone for PaDiM/PatchCore feature extraction.",
        license="BSD-3 (torchvision weights) — verify ImageNet terms before use",
        source_url="https://pytorch.org/vision/stable/models.html",
        expected_sha256="",   # operator records the real digest when approving
        approved=False,        # BLOCKED: awaiting license + data-rights verification
        rights_cleared=False,
        requires_file=True,
        architecture="resnet18",
        preprocessing={
            "resize": [256, 256], "center_crop": [224, 224], "interpolation": "bilinear",
            "mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225],
        },
    ),
    # Deterministic, no-weights backbone for CPU anomaly-localization smoke tests.
    # Explicitly NOT a learned model; produces engineering heatmaps, not science.
    "stub_backbone": CheckpointRecord(
        checkpoint_id="stub_backbone",
        description="Deterministic Pillow-based stub backbone for anomaly-localization smoke tests ONLY.",
        license="n/a (internal stub)",
        source_url="",
        expected_sha256="",
        approved=True,
        rights_cleared=True,
        requires_file=False,
        architecture="stub",
        preprocessing={"resize": [96, 96], "mean": [0.0, 0.0, 0.0], "std": [1.0, 1.0, 1.0]},
    ),
}


def register_operator_approved_checkpoint(
    checkpoint_id: str, *, file_path: str, architecture: str, license: str, source_url: str,
    description: str, preprocessing: dict | None = None, compatibility_policy: dict | None = None,
    approver_id: str = "", license_evidence_ref: str = "", source_evidence_ref: str = "",
    research_execution_only: bool = False,
) -> CheckpointRecord:
    """Register a checkpoint an OPERATOR approved in an isolated research environment,
    computing and recording the on-disk file's SHA-256. **Fail-closed (Stage 6B).**

    An authenticated ``approver_id`` is always required. Then:

    * ``research_execution_only=True`` — a locally-generated / non-scientific backbone
      (its ``compatibility_policy`` is ``scientifically_valid=False``). It is cleared
      for pipeline EXECUTION only; ``scientific_use_approved`` stays False, so
      :func:`assert_scientific_checkpoint` refuses it for any performance claim.
    * otherwise (a real scientific backbone) — rights clearance AND scientific use
      require **verifiable license and source evidence** (``license_evidence_ref`` +
      ``source_evidence_ref``) and genuinely scientific weights. Without that evidence
      the record is registered with ``rights_cleared=False`` and
      ``scientific_use_approved=False``, so ``verify_checkpoint`` refuses it.

    Never downloads anything; the record requires the file and is digest-verified, so
    a later file swap is rejected.
    """
    if not os.path.exists(file_path):
        raise CheckpointFileMissingError(f"No checkpoint file at {file_path!r} to approve.")
    if not str(approver_id or "").strip():
        raise CheckpointRightsError(
            f"Checkpoint '{checkpoint_id}' requires an authenticated approver_id (fail-closed)."
        )
    policy_sci_valid = (compatibility_policy or {}).get("scientifically_valid", True)
    has_evidence = bool(str(license_evidence_ref or "").strip() and str(source_evidence_ref or "").strip())

    if research_execution_only:
        rights_cleared = True              # may be CONSTRUCTED / run for pipeline verification
        scientific_use_approved = False    # never for scientific performance claims
    else:
        rights_cleared = has_evidence
        scientific_use_approved = has_evidence and bool(policy_sci_valid)

    digest = _file_sha256(file_path)
    rec = CheckpointRecord(
        checkpoint_id=checkpoint_id, description=description, license=license, source_url=source_url,
        expected_sha256=digest, approved=True, rights_cleared=rights_cleared, requires_file=True,
        architecture=architecture, preprocessing=preprocessing, compatibility_policy=compatibility_policy,
        approver_id=str(approver_id).strip(), license_evidence_ref=str(license_evidence_ref or "").strip(),
        source_evidence_ref=str(source_evidence_ref or "").strip(), scientific_use_approved=scientific_use_approved,
    )
    _REGISTRY[checkpoint_id] = rec
    return rec


def assert_scientific_checkpoint(record: CheckpointRecord) -> None:
    """Fail-closed: raise unless a checkpoint may back a SCIENTIFIC performance claim.

    Requires it to be approved, rights-cleared, carry verifiable license + source
    evidence, and be approved for scientific use (which excludes random-weight /
    research-execution backbones). A benchmark that reports scientific metrics must
    call this first.
    """
    if not (record.approved and record.rights_cleared):
        raise CheckpointScientificUseError(
            f"Checkpoint '{record.checkpoint_id}' is not approved/rights-cleared."
        )
    if not record.scientific_use_approved:
        raise CheckpointScientificUseError(
            f"Checkpoint '{record.checkpoint_id}' is NOT approved for scientific performance claims "
            "(random-weight / research-execution backbone, or missing license/source evidence)."
        )
    if not (record.license_evidence_ref and record.source_evidence_ref and record.approver_id):
        raise CheckpointScientificUseError(
            f"Checkpoint '{record.checkpoint_id}' lacks authenticated approval or license/source evidence."
        )


def get_record(checkpoint_id: str) -> CheckpointRecord:
    rec = _REGISTRY.get(checkpoint_id)
    if rec is None:
        raise CheckpointNotRegisteredError(
            f"Checkpoint '{checkpoint_id}' is not in the approval registry."
        )
    return rec


def _file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_checkpoint(checkpoint_id: str, *, file_path: str | None = None) -> CheckpointRecord:
    """Fail-closed verification that a checkpoint may be loaded for research.

    Checks registry membership, approval, rights clearance, and — for a real
    weights file — that the file exists and its content digest matches the
    registered ``expected_sha256``. Never downloads anything.
    """
    rec = get_record(checkpoint_id)
    if not rec.approved:
        raise CheckpointNotApprovedError(
            f"Checkpoint '{checkpoint_id}' is not approved for research use "
            "(awaiting explicit human approval)."
        )
    if not rec.rights_cleared:
        raise CheckpointRightsError(
            f"Checkpoint '{checkpoint_id}' does not have verified data/usage rights."
        )
    if rec.requires_file:
        if not file_path or not os.path.exists(file_path):
            raise CheckpointFileMissingError(
                f"Checkpoint '{checkpoint_id}' requires an on-disk weights file; none was found "
                f"at {file_path!r}. Weights are never downloaded automatically or committed."
            )
        if not rec.expected_sha256:
            raise CheckpointVerificationError(
                f"Checkpoint '{checkpoint_id}' has no registered expected_sha256 to verify against."
            )
        actual = _file_sha256(file_path)
        if actual != rec.expected_sha256:
            raise CheckpointVerificationError(
                f"Checkpoint '{checkpoint_id}' file digest {actual} does not match the "
                f"registered digest {rec.expected_sha256}."
            )
    return rec
