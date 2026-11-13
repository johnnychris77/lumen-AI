"""Research-artifact integrity (Stage 5C).

Heatmaps and other research artifacts are persisted to a tenant-scoped,
access-controlled store. A heatmap REFERENCE is returned only when the artifact is
actually stored and resolvable; otherwise no reference is returned. Malformed
masks/dimensions are rejected before evaluation, and non-finite numeric outputs
are never emitted.
"""
from __future__ import annotations

import json
import math
import os


class MalformedMaskError(ValueError):
    """A mask is not a rectangular binary grid of the expected dimensions."""


class MalformedHeatmapError(ValueError):
    """A heatmap is empty, non-rectangular, or contains non-finite values."""


class NonFiniteValueError(ValueError):
    """A numeric output was NaN or infinite."""


class TenantAccessError(PermissionError):
    """A heatmap/artifact was requested by a tenant that does not own it."""


def sanitize_score(x) -> float:
    """Return a finite float or raise — never emit NaN/inf as a research output."""
    if not isinstance(x, (int, float)) or not math.isfinite(x):
        raise NonFiniteValueError(f"Non-finite numeric output: {x!r}")
    return float(x)


def validate_heatmap(heatmap) -> tuple[int, int]:
    """Ensure a heatmap is a non-empty rectangular grid of finite numbers. Returns
    (height, width)."""
    if not heatmap or not isinstance(heatmap, list) or not heatmap[0]:
        raise MalformedHeatmapError("Heatmap is empty.")
    w = len(heatmap[0])
    for row in heatmap:
        if len(row) != w:
            raise MalformedHeatmapError("Heatmap is not rectangular.")
        for v in row:
            if not isinstance(v, (int, float)) or not math.isfinite(v):
                raise MalformedHeatmapError("Heatmap contains a non-finite value.")
    return len(heatmap), w


def validate_mask(mask, *, width: int, height: int) -> None:
    """Ensure a mask is a rectangular binary grid matching (height, width)."""
    if not mask or len(mask) != height or any(len(row) != width for row in mask):
        raise MalformedMaskError(f"Mask dimensions do not match image ({height}x{width}).")
    for row in mask:
        for v in row:
            if v not in (0, 1, True, False):
                raise MalformedMaskError("Mask must be binary (0/1).")


class ResearchArtifactStore:
    """A tenant-scoped, on-disk research-artifact store (access-controlled by the
    filesystem permissions of ``base_dir``). Never writes outside ``base_dir``."""

    def __init__(self, base_dir: str):
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def _safe_component(self, s) -> str:
        return "".join(c for c in str(s) if c.isalnum() or c in "-_.") or "x"

    def _path(self, tenant_id: str, run_id: str, image_id) -> str:
        return os.path.join(
            self.base_dir, self._safe_component(tenant_id), self._safe_component(run_id),
            f"{self._safe_component(image_id)}.json",
        )

    def store_heatmap(self, *, tenant_id: str, run_id: str, image_id, heatmap) -> str | None:
        """Validate + persist a heatmap; return a resolvable ref, or None if it
        could not be stored (never a dangling reference). The ref is owned by
        ``tenant_id`` and can only be resolved by that tenant."""
        try:
            validate_heatmap(heatmap)
        except MalformedHeatmapError:
            return None
        path = self._path(tenant_id, run_id, image_id)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"tenant_id": tenant_id, "run_id": run_id, "image_id": image_id, "heatmap": heatmap}, f)
        except OSError:
            return None
        ref = f"artifact://{self._safe_component(tenant_id)}/{self._safe_component(run_id)}/{self._safe_component(image_id)}"
        # Confirm readback as the owning tenant (never a dangling reference).
        return ref if self.resolve(ref, requesting_tenant_id=tenant_id) else None

    def _owner_tenant(self, ref: str) -> str | None:
        parts = ref[len("artifact://"):].split("/")
        return parts[0] if len(parts) == 3 else None

    def resolve(self, ref: str | None, *, requesting_tenant_id: str) -> str | None:
        """Return the on-disk path for a ref if it exists, is readable, AND is
        owned by ``requesting_tenant_id``. Cross-tenant access returns None — a
        tenant can never resolve another tenant's research artifact.

        ``requesting_tenant_id`` is required: retrieval is always tenant-scoped.
        """
        if not str(requesting_tenant_id or "").strip():
            raise TenantAccessError("A requesting_tenant_id is required to resolve a research artifact.")
        if not ref or not ref.startswith("artifact://"):
            return None
        parts = ref[len("artifact://"):].split("/")
        if len(parts) != 3:
            return None
        tenant_id, run_id, image_id = parts
        # Tenant authorization: the ref's tenant must match the requester.
        if tenant_id != self._safe_component(requesting_tenant_id):
            return None
        path = self._path(tenant_id, run_id, image_id)
        if not (os.path.exists(path) and os.access(path, os.R_OK)):
            return None
        # Defense in depth: the stored payload's tenant must also match.
        try:
            with open(path, encoding="utf-8") as f:
                stored_tenant = self._safe_component(json.load(f).get("tenant_id", ""))
        except (OSError, ValueError):
            return None
        return path if stored_tenant == tenant_id else None

    def exists(self, ref: str | None, *, requesting_tenant_id: str) -> bool:
        return self.resolve(ref, requesting_tenant_id=requesting_tenant_id) is not None
