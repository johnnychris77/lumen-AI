"""Research-only anomaly localizers (Stage 5B).

One interface, three providers:

* ``StubLocalizer`` — a deterministic, Pillow-only normal-only localizer for CPU
  smoke tests. It fits a per-pixel diagonal-Gaussian model over VERIFIED-NORMAL
  images and produces a genuine pixel-level anomaly map at the INPUT image
  resolution (spatial alignment preserved). It is explicitly NOT Anomalib PaDiM
  and produces engineering heatmaps, not scientific performance.
* ``PadimLocalizer`` / ``PatchCoreLocalizer`` — the real Anomalib backends. They
  require torch + Anomalib AND an explicitly approved, rights-cleared,
  hash-verified backbone checkpoint; construction is refused otherwise (the
  documented Stage 5B blocker). No weight is ever auto-downloaded.

Scores are UNCALIBRATED. No localizer maps an anomaly to a clinical diagnosis,
severity, or release decision.
"""
from __future__ import annotations

import os
from collections import deque

from research.lens_vision.anomaly_feasibility import AnomalyRegion
from research.lens_vision.checkpoint import verify_checkpoint
from research.lens_vision.deps import require_torch
from research.lens_vision.images import decode_rgb

_EPS = 1e-6


def _original_size(image_bytes: bytes | None) -> tuple[int, int]:
    """The original (width, height) of an image, with safe decoding."""
    import io  # noqa: PLC0415

    from PIL import Image, UnidentifiedImageError  # noqa: PLC0415

    from research.lens_vision.images import InvalidImageError
    if not image_bytes:
        raise InvalidImageError("No image bytes provided.")
    try:
        return Image.open(io.BytesIO(image_bytes)).convert("RGB").size
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise InvalidImageError(f"Could not decode image bytes: {exc}") from exc


class AnomalyLocalizer:
    name = "base"
    backbone = ""

    def fit(self, normal_images: list[bytes]) -> "AnomalyLocalizer":  # pragma: no cover - interface
        raise NotImplementedError

    def score(self, image_bytes: bytes | None) -> tuple[list[list[float]], float]:  # pragma: no cover
        """Return (heatmap[H][W] at the ORIGINAL image resolution, image_level_score)."""
        raise NotImplementedError


class StubLocalizer(AnomalyLocalizer):
    """Deterministic diagonal-Gaussian per-pixel localizer (smoke tests only)."""

    name = "stub_padim_like"
    backbone = "stub"

    def __init__(self, *, proc_size: tuple[int, int] = (64, 64)):
        self.proc_size = proc_size
        self._mean: list[list[list[float]]] | None = None
        self._var: list[list[list[float]]] | None = None
        self._fitted_on = 0

    def fit(self, normal_images: list[bytes]) -> "StubLocalizer":
        if not normal_images:
            raise ValueError("StubLocalizer.fit requires at least one verified-normal image.")
        w, h = self.proc_size
        n = len(normal_images)
        sums = [[[0.0, 0.0, 0.0] for _ in range(w)] for _ in range(h)]
        sqs = [[[0.0, 0.0, 0.0] for _ in range(w)] for _ in range(h)]
        for b in normal_images:
            img = decode_rgb(b, size=self.proc_size)
            px = img.load()
            for y in range(h):
                for x in range(w):
                    r, g, bl = px[x, y]
                    for c, v in enumerate((r, g, bl)):
                        fv = v / 255.0
                        sums[y][x][c] += fv
                        sqs[y][x][c] += fv * fv
        self._mean = [[[sums[y][x][c] / n for c in range(3)] for x in range(w)] for y in range(h)]
        self._var = [[[max(_EPS, sqs[y][x][c] / n - (sums[y][x][c] / n) ** 2) for c in range(3)]
                      for x in range(w)] for y in range(h)]
        self._fitted_on = n
        return self

    def score(self, image_bytes: bytes | None) -> tuple[list[list[float]], float]:
        if self._mean is None or self._var is None:
            raise RuntimeError("StubLocalizer must be fit() on normal images before scoring.")
        # Original size (to preserve input dimensions) + processing size (to score).
        orig_w, orig_h = _original_size(image_bytes)
        proc = decode_rgb(image_bytes, size=self.proc_size)
        w, h = self.proc_size
        px = proc.load()
        small = [[0.0 for _ in range(w)] for _ in range(h)]
        for y in range(h):
            for x in range(w):
                r, g, bl = px[x, y]
                s = 0.0
                for c, v in enumerate((r, g, bl)):
                    fv = v / 255.0
                    s += (fv - self._mean[y][x][c]) ** 2 / self._var[y][x][c]
                small[y][x] = s
        # Upsample (nearest) to the ORIGINAL resolution so the heatmap aligns with
        # the input image pixel-for-pixel.
        heatmap = [[small[int(y * h / orig_h)][int(x * w / orig_w)] for x in range(orig_w)]
                   for y in range(orig_h)]
        image_score = max(max(row) for row in small)
        return heatmap, image_score


def _governed_backbone(checkpoint_id: str, file_path: str | None):
    """Verify a backbone checkpoint for an Anomalib localizer (fail-closed)."""
    record = verify_checkpoint(checkpoint_id, file_path=file_path)
    require_torch()
    return record


# Pinned Anomalib release this adapter targets. The 0.x and 1.x APIs differ; the
# code below uses the 1.1.x model/engine interface. VERIFY the installed version
# matches before running in an isolated research environment.
ANOMALIB_PINNED = "1.1"


class _AnomalibLocalizer(AnomalyLocalizer):
    """Base for the REAL Anomalib backends (PaDiM, PatchCore).

    Construction is fail-closed: it refuses unless the backbone checkpoint is
    approved + rights-cleared + SHA-256-verified AND torch + a compatible Anomalib
    are installed. The approved backbone weights are loaded from the verified local
    file; Anomalib's own pretrained download is DISABLED (``pre_trained=False``) so
    no weights are ever fetched automatically. These methods run only in an
    isolated research environment — they are a genuine implementation, never a
    stub, and are reported BLOCKED where the environment is unavailable.
    """

    anomalib_model = ""  # "padim" | "patchcore"

    def __init__(self, *, backbone_checkpoint_id: str = "resnet18_imagenet", file_path: str | None = None):
        self.record = _governed_backbone(backbone_checkpoint_id, file_path)
        self.backbone = self.record.architecture
        self.preprocessing = self.record.preprocessing or {}
        self.digest = self.record.expected_sha256
        self.backbone_file_path = file_path
        self._require_anomalib()
        self._model = None
        self._engine = None
        # Populated by _build_model() once real weights are verified + loaded.
        self.load_report = None
        self.backbone_scientifically_valid = True

    @staticmethod
    def _require_anomalib() -> None:
        import importlib.util  # noqa: PLC0415
        if importlib.util.find_spec("anomalib") is None:  # pragma: no cover - needs anomalib
            from research.lens_vision.deps import ResearchDependencyMissing
            raise ResearchDependencyMissing(
                f"Anomalib is not installed. Install backend/requirements-research.txt (anomalib~={ANOMALIB_PINNED}) "
                "in an isolated research environment; verify the Anomalib API version before use."
            )

    def _build_model(self):  # pragma: no cover - requires isolated torch+anomalib env
        from anomalib.models import Padim, Patchcore  # noqa: PLC0415  (anomalib 1.1.x)

        from research.lens_vision.backbone_loader import (  # noqa: PLC0415
            CompatibilityPolicy,
            load_verified_backbone,
            safe_torch_load,
            set_offline_environment,
        )

        # Defense in depth: forbid implicit weight downloads during construction.
        set_offline_environment()

        layers = ["layer1", "layer2", "layer3"]
        if self.anomalib_model == "padim":
            model = Padim(backbone=self.backbone, layers=layers, pre_trained=False)
        elif self.anomalib_model == "patchcore":
            model = Patchcore(
                backbone=self.backbone, layers=layers, pre_trained=False,
                coreset_sampling_ratio=getattr(self, "coreset_sampling_ratio", 0.1),
            )
        else:  # pragma: no cover
            raise ValueError(self.anomalib_model)

        # Load the APPROVED, verified backbone weights from the local file — never a
        # download, never arbitrary pickled code (weights_only), and never a silent
        # partial/uninitialized backbone (names + shapes verified before loading).
        state = safe_torch_load(self.backbone_file_path, map_location="cpu")
        feat = getattr(model.model, "feature_extractor", None) or getattr(model.model, "backbone", None)
        if feat is None:  # pragma: no cover - defensive: unknown anomalib layout
            from research.lens_vision.backbone_loader import BackboneInitializationError
            raise BackboneInitializationError(
                "Could not locate the backbone feature extractor on the Anomalib model to verify weight loading."
            )
        policy = None
        if self.record.compatibility_policy:
            policy = CompatibilityPolicy(**self.record.compatibility_policy)
        self.load_report = load_verified_backbone(feat, state, policy=policy)
        # Carry the honest scientific-validity flag from the compatibility policy.
        self.backbone_scientifically_valid = self.load_report.scientifically_valid

        for p in model.parameters():
            p.requires_grad_(False)
        model.eval()
        return model

    def fit(self, normal_images: list[bytes]) -> "_AnomalibLocalizer":  # pragma: no cover - needs env
        import tempfile  # noqa: PLC0415

        from anomalib.data import Folder  # noqa: PLC0415
        from anomalib.engine import Engine  # noqa: PLC0415
        from research.lens_vision.images import decode_rgb

        if not normal_images:
            raise ValueError("fit requires at least one verified-normal image.")
        self._model = self._build_model()
        # Materialize the verified-normal images to an access-controlled temp dir,
        # then fit PaDiM/PatchCore on the 'normal' split only (no abnormal images).
        self._tmpdir = tempfile.mkdtemp(prefix="lumen_anom_fit_")
        size = tuple(self.preprocessing.get("resize", [256, 256]))
        for i, b in enumerate(normal_images):
            decode_rgb(b, size=size).save(os.path.join(self._tmpdir, f"normal_{i:05d}.png"))
        datamodule = Folder(name="lumen_research", root=self._tmpdir, normal_dir=".")
        self._engine = Engine(accelerator="cpu")
        self._engine.fit(model=self._model, datamodule=datamodule)
        return self

    def score(self, image_bytes: bytes | None):  # pragma: no cover - needs env
        import torch  # noqa: PLC0415

        from research.lens_vision.images import decode_rgb
        if self._model is None:
            raise RuntimeError("Localizer must be fit() before scoring.")
        orig_w, orig_h = _original_size(image_bytes)
        size = tuple(self.preprocessing.get("resize", [256, 256]))
        mean = self.preprocessing.get("mean", [0.485, 0.456, 0.406])
        std = self.preprocessing.get("std", [0.229, 0.224, 0.225])
        import numpy as np  # noqa: PLC0415
        arr = (np.asarray(decode_rgb(image_bytes, size=size), dtype="float32") / 255.0 - mean) / std
        tensor = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)
        with torch.no_grad():
            out = self._model.model(tensor)
        amap = out["anomaly_map"] if isinstance(out, dict) else out
        amap = torch.nn.functional.interpolate(
            amap.view(1, 1, *amap.shape[-2:]), size=(orig_h, orig_w), mode="bilinear", align_corners=False
        ).squeeze().tolist()
        image_score = float(max(max(r) for r in amap))
        return amap, image_score


class PadimLocalizer(_AnomalibLocalizer):
    """Anomalib PaDiM over a frozen, approved backbone. Governed + torch-required."""

    name = "padim"
    anomalib_model = "padim"


class PatchCoreLocalizer(_AnomalibLocalizer):
    """Anomalib PatchCore comparison model (same governed research interface)."""

    name = "patchcore"
    anomalib_model = "patchcore"

    def __init__(self, *, backbone_checkpoint_id: str = "resnet18_imagenet", file_path: str | None = None,
                 coreset_sampling_ratio: float = 0.1):
        self.coreset_sampling_ratio = coreset_sampling_ratio
        super().__init__(backbone_checkpoint_id=backbone_checkpoint_id, file_path=file_path)


def propose_regions(
    heatmap: list[list[float]], *, threshold: float, max_regions: int = 5,
) -> list[AnomalyRegion]:
    """Threshold a heatmap and return research-only bounding-box regions for the
    largest-score connected components. Scores are UNCALIBRATED and uncertainty is
    left unmeasured (recorded by the caller as 'unknown', not fabricated)."""
    if not heatmap or not heatmap[0]:
        return []
    h, w = len(heatmap), len(heatmap[0])
    visited = [[False] * w for _ in range(h)]
    regions: list[AnomalyRegion] = []
    for sy in range(h):
        for sx in range(w):
            if visited[sy][sx] or heatmap[sy][sx] < threshold:
                continue
            # BFS connected component (4-neighbour) of above-threshold pixels.
            q = deque([(sy, sx)])
            visited[sy][sx] = True
            minx = maxx = sx
            miny = maxy = sy
            peak = heatmap[sy][sx]
            while q:
                cy, cx = q.popleft()
                peak = max(peak, heatmap[cy][cx])
                minx, maxx = min(minx, cx), max(maxx, cx)
                miny, maxy = min(miny, cy), max(maxy, cy)
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < h and 0 <= nx < w and not visited[ny][nx] and heatmap[ny][nx] >= threshold:
                        visited[ny][nx] = True
                        q.append((ny, nx))
            regions.append(AnomalyRegion(
                x=float(minx), y=float(miny), width=float(maxx - minx + 1), height=float(maxy - miny + 1),
                anomaly_score=float(peak), uncertainty=None,  # unmeasured -> reported as 'unknown'
            ))
    regions.sort(key=lambda r: r.anomaly_score, reverse=True)
    return regions[:max_regions]
