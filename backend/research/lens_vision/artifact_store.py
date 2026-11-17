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

    @staticmethod
    def _encode(s) -> str:
        """Injective, filesystem- and traversal-safe encoding of an identity component.

        SEC-176/RGI-04: the previous ``_safe_component`` *stripped* unsupported
        characters, which is NOT injective — distinct tenants such as ``"a/b"`` and
        ``"ab"`` collapsed to the same component, so one tenant's run/image path (and its
        tenant-equality check) collided with another's, defeating isolation; it also kept
        ``.`` so a component of ``".."`` enabled path traversal out of ``base_dir``.

        This encodes the raw UTF-8 bytes as lowercase hex: the mapping is a bijection on
        the input (no two distinct identities collide) and the output is ``[0-9a-f]+``
        only, so a component can never be ``/``, ``.`` or ``..``. An empty identity is
        rejected (fail-closed) — an artifact cannot be tenant-scoped without a tenant.
        """
        raw = str(s)
        if raw == "":
            raise TenantAccessError("An empty artifact identity component is not allowed (fail-closed).")
        return raw.encode("utf-8").hex()

    @staticmethod
    def _is_hex_component(p: str) -> bool:
        return bool(p) and all(c in "0123456789abcdef" for c in p)

    def _path_enc(self, enc_tenant: str, enc_run: str, enc_image: str) -> str:
        """Build the on-disk path from ALREADY-ENCODED (hex) components. Hex can hold no
        path separator or ``..`` token, so the join can never escape ``base_dir``."""
        return os.path.join(self.base_dir, enc_tenant, enc_run, f"{enc_image}.json")

    def store_heatmap(self, *, tenant_id: str, run_id: str, image_id, heatmap) -> str | None:
        """Validate + persist a heatmap; return a resolvable ref, or None if it
        could not be stored (never a dangling reference). The ref is owned by
        ``tenant_id`` and can only be resolved by that tenant. Distinct tenants can
        never share a path or overwrite each other's artifact (injective encoding)."""
        try:
            validate_heatmap(heatmap)
        except MalformedHeatmapError:
            return None
        try:
            enc_t, enc_r, enc_i = self._encode(tenant_id), self._encode(run_id), self._encode(image_id)
        except TenantAccessError:
            return None  # a tenant-less / id-less artifact cannot be tenant-scoped
        path = self._path_enc(enc_t, enc_r, enc_i)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            # Atomic persistence: write to a temp file in the same directory, then
            # os.replace (atomic on POSIX) so a reader never sees a torn/partial file
            # and a crash mid-write cannot corrupt an existing artifact.
            tmp = f"{path}.{os.getpid()}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"tenant_id": tenant_id, "run_id": run_id, "image_id": image_id, "heatmap": heatmap}, f)
            os.replace(tmp, path)
        except OSError:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except (OSError, NameError):
                pass
            return None
        ref = f"artifact://{enc_t}/{enc_r}/{enc_i}"
        # Confirm readback as the owning tenant (never a dangling reference).
        return ref if self.resolve(ref, requesting_tenant_id=tenant_id) else None

    def _owner_tenant(self, ref: str) -> str | None:
        """The encoded owning-tenant component of a ref (hex), or None if malformed."""
        parts = ref[len("artifact://"):].split("/")
        return parts[0] if len(parts) == 3 and self._is_hex_component(parts[0]) else None

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
        enc_tenant, enc_run, enc_image = parts
        # Defense in depth: ref components must be valid hex (as produced by _encode);
        # anything else (e.g. a crafted ".." or injected separator) is rejected before
        # it can touch the filesystem.
        if not all(self._is_hex_component(p) for p in parts):
            return None
        # Tenant authorization: the ref's (encoded) tenant must match the requester's.
        try:
            if enc_tenant != self._encode(requesting_tenant_id):
                return None
        except TenantAccessError:
            return None
        path = self._path_enc(enc_tenant, enc_run, enc_image)
        if not (os.path.exists(path) and os.access(path, os.R_OK)):
            return None
        # Defense in depth: the stored payload's tenant must also match the ref's tenant.
        try:
            with open(path, encoding="utf-8") as f:
                stored_tenant = self._encode(json.load(f).get("tenant_id", ""))
        except (OSError, ValueError, TenantAccessError):
            return None
        return path if stored_tenant == enc_tenant else None

    def exists(self, ref: str | None, *, requesting_tenant_id: str) -> bool:
        return self.resolve(ref, requesting_tenant_id=requesting_tenant_id) is not None
