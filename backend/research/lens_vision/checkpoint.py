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
}


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
