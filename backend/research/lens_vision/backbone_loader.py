"""Stage 5D hardening — safe, verified backbone-weight loading.

Stage 5C loaded backbone weights with a bare ``torch.load(...)`` followed by
``load_state_dict(state, strict=False)``. That had three weaknesses this module
corrects:

1. **Unsafe deserialization.** ``torch.load`` unpickles arbitrary Python by
   default, so a malicious checkpoint file could execute code. We load with
   ``weights_only=True`` and refuse if the installed torch cannot do that.
2. **Silent partial loading.** ``strict=False`` silently tolerates missing or
   mismatched tensors, so a run could proceed on an *uninitialized or partially
   initialized* backbone. We verify the state dict against the target module's
   tensor **names and shapes** and refuse unless coverage is complete.
3. **Undocumented deviations.** A deviation from full, exact loading is allowed
   only when an explicit, documented :class:`CompatibilityPolicy` authorizes it —
   and a policy can mark itself ``scientifically_valid=False`` (e.g. a
   research-execution-only smoke backbone), which the caller must surface.

Nothing here downloads weights or reaches the network; callers pass a local file
that already passed the checkpoint approval + SHA-256 gate.
"""
from __future__ import annotations

from dataclasses import dataclass, field


class UnsafeCheckpointError(RuntimeError):
    """The checkpoint could not be deserialized safely (weights-only refused)."""


class BackboneArchitectureMismatchError(RuntimeError):
    """A checkpoint tensor does not match the backbone's expected shape/name."""


class BackboneInitializationError(RuntimeError):
    """The backbone would be left uninitialized or only partially initialized."""


@dataclass(frozen=True)
class CompatibilityPolicy:
    """An explicit, documented authorization to deviate from full exact loading.

    The default (no policy) requires that EVERY backbone tensor is populated from
    the checkpoint with an exactly matching shape. A policy may relax that, but it
    must say why, and it must declare whether the resulting backbone is
    scientifically valid. A research-execution-only policy sets
    ``scientifically_valid=False`` so downstream records can never be mistaken for
    validated science.
    """

    policy_id: str
    reason: str
    min_coverage: float = 1.0          # fraction of target tensors that must load
    allow_missing_keys: bool = False   # tolerate target tensors absent from the ckpt
    allow_shape_mismatch: bool = False # NEVER for science; last-resort research only
    scientifically_valid: bool = True  # False => execution smoke only, not science

    def __post_init__(self):
        if not (0.0 <= self.min_coverage <= 1.0):
            raise ValueError("min_coverage must be in [0, 1].")
        if not str(self.policy_id).strip() or not str(self.reason).strip():
            raise ValueError("A compatibility policy must document a policy_id and reason.")


@dataclass
class BackboneLoadReport:
    """What actually happened when weights were loaded into the backbone."""

    n_target_tensors: int
    matched: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)            # in module, absent from ckpt
    unexpected: list[str] = field(default_factory=list)         # in ckpt, absent from module
    shape_mismatch: list[tuple] = field(default_factory=list)   # (name, ckpt_shape, module_shape)
    coverage: float = 0.0
    policy_id: str | None = None
    scientifically_valid: bool = True

    def to_dict(self) -> dict:
        return {
            "n_target_tensors": self.n_target_tensors,
            "n_matched": len(self.matched),
            "n_missing": len(self.missing),
            "n_unexpected": len(self.unexpected),
            "n_shape_mismatch": len(self.shape_mismatch),
            "coverage": round(self.coverage, 6),
            "policy_id": self.policy_id,
            "scientifically_valid": self.scientifically_valid,
            "missing": self.missing[:20],
            "shape_mismatch": [list(x) for x in self.shape_mismatch[:20]],
        }


def _extract_state_dict(obj):
    """Pull a plain name->tensor mapping out of a loaded checkpoint object."""
    if isinstance(obj, dict) and "state_dict" in obj and isinstance(obj["state_dict"], dict):
        obj = obj["state_dict"]
    if not isinstance(obj, dict):
        raise UnsafeCheckpointError("Checkpoint did not deserialize to a state-dict mapping.")
    return obj


def safe_torch_load(path: str, *, map_location: str = "cpu") -> dict:
    """``torch.load`` with ``weights_only=True`` — never executes pickled code.

    Refuses rather than silently falling back to unsafe unpickling on a torch too
    old to support ``weights_only``.
    """
    import torch  # noqa: PLC0415

    try:
        obj = torch.load(path, map_location=map_location, weights_only=True)
    except TypeError as exc:  # pragma: no cover - only on very old torch
        raise UnsafeCheckpointError(
            "Installed torch does not support weights_only loading; refusing unsafe "
            "checkpoint deserialization (arbitrary-code-execution risk)."
        ) from exc
    except Exception as exc:
        # weights_only rejects a checkpoint that pickled arbitrary globals.
        raise UnsafeCheckpointError(
            f"Checkpoint at {path!r} could not be loaded under weights_only "
            f"deserialization: {exc}"
        ) from exc
    return _extract_state_dict(obj)


def verify_state_dict_against_module(state: dict, module) -> BackboneLoadReport:
    """Compare a checkpoint state dict to a module's tensors by name and shape."""
    target = module.state_dict()
    matched: list[str] = []
    shape_mismatch: list[tuple] = []
    for name, tgt in target.items():
        if name in state:
            src_shape = tuple(getattr(state[name], "shape", ()))
            tgt_shape = tuple(getattr(tgt, "shape", ()))
            if src_shape == tgt_shape:
                matched.append(name)
            else:
                shape_mismatch.append((name, src_shape, tgt_shape))
    missing = [n for n in target if n not in state]
    unexpected = [n for n in state if n not in target]
    n_target = max(1, len(target))
    return BackboneLoadReport(
        n_target_tensors=len(target),
        matched=matched,
        missing=missing,
        unexpected=unexpected,
        shape_mismatch=shape_mismatch,
        coverage=len(matched) / n_target,
    )


def load_verified_backbone(module, state: dict, *, policy: CompatibilityPolicy | None = None) -> BackboneLoadReport:
    """Load ``state`` into ``module`` only after verifying names and shapes.

    Fail-closed: a shape mismatch, missing tensors, or coverage below the policy
    threshold raises rather than silently leaving the backbone uninitialized.
    Deviations are authorized only by an explicit :class:`CompatibilityPolicy`.
    """
    report = verify_state_dict_against_module(state, module)
    report.policy_id = policy.policy_id if policy else None
    report.scientifically_valid = policy.scientifically_valid if policy else True

    min_cov = policy.min_coverage if policy else 1.0
    allow_missing = policy.allow_missing_keys if policy else False
    allow_shape = policy.allow_shape_mismatch if policy else False

    if report.shape_mismatch and not allow_shape:
        raise BackboneArchitectureMismatchError(
            f"Backbone/checkpoint architecture mismatch: {len(report.shape_mismatch)} tensor(s) "
            f"have incompatible shapes (e.g. {report.shape_mismatch[0]}). No compatibility policy "
            "authorizes a shape mismatch."
        )
    if report.coverage < min_cov:
        raise BackboneInitializationError(
            f"Backbone would be only {report.coverage:.1%} initialized from the checkpoint "
            f"(< required {min_cov:.1%}); refusing an uninitialized/partially initialized backbone. "
            "Authorize explicitly with a documented CompatibilityPolicy if this is intended."
        )
    if report.missing and not allow_missing:
        raise BackboneInitializationError(
            f"{len(report.missing)} backbone tensor(s) are absent from the checkpoint "
            f"(e.g. {report.missing[0]}); refusing a partially initialized backbone without a "
            "documented CompatibilityPolicy(allow_missing_keys=True)."
        )
    # Verified safe: names/shapes checked above. strict=False is acceptable now
    # because any missing/unexpected keys were explicitly authorized.
    module.load_state_dict(state, strict=False)
    return report


def set_offline_environment() -> None:
    """Best-effort: forbid implicit model/weight downloads during a research build.

    Sets the common offline switches so a backbone construction that mistakenly
    tries to fetch pretrained weights fails loudly instead of reaching the network.
    The approval gate + ``pre_trained=False`` are the primary controls; this is
    defense in depth.
    """
    import os  # noqa: PLC0415

    for var in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE"):
        os.environ.setdefault(var, "1")
    # torchvision/torch.hub honor a writable cache; point it at a scratch dir but
    # never populate it from the network (callers must pass local weights).
    os.environ.setdefault("TORCH_HUB_DISABLE_DOWNLOAD", "1")
