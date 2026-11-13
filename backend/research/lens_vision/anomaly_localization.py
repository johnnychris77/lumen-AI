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


class PadimLocalizer(AnomalyLocalizer):
    """Anomalib PaDiM over a frozen, approved backbone. Governed + torch-required."""

    name = "padim"

    def __init__(self, *, backbone_checkpoint_id: str = "resnet18_imagenet", file_path: str | None = None):
        # Governance first: refuses unless approved + rights-cleared + hash-verified,
        # and refuses if torch/Anomalib are absent. No auto-download.
        self.record = _governed_backbone(backbone_checkpoint_id, file_path)
        self.backbone = self.record.architecture
        self.preprocessing = self.record.preprocessing or {}
        self.digest = self.record.expected_sha256
        self._require_anomalib()

    @staticmethod
    def _require_anomalib() -> None:
        import importlib.util  # noqa: PLC0415
        if importlib.util.find_spec("anomalib") is None:  # pragma: no cover - needs anomalib
            from research.lens_vision.deps import ResearchDependencyMissing
            raise ResearchDependencyMissing(
                "Anomalib is not installed. Install backend/requirements-research.txt in an "
                "isolated research environment; verify the Anomalib API version before use."
            )

    def fit(self, normal_images: list[bytes]) -> "PadimLocalizer":  # pragma: no cover - needs anomalib
        raise NotImplementedError(
            "The real Anomalib PaDiM fit runs only in an isolated research environment with "
            "an approved backbone checkpoint; see docs/model-development/STAGE_5B_ANOMALY_LOCALIZATION.md."
        )

    def score(self, image_bytes):  # pragma: no cover - needs anomalib
        raise NotImplementedError


class PatchCoreLocalizer(PadimLocalizer):
    """Anomalib PatchCore comparison model (same governed interface as PaDiM)."""

    name = "patchcore"

    def __init__(self, *, backbone_checkpoint_id: str = "resnet18_imagenet", file_path: str | None = None,
                 coreset_sampling_ratio: float = 0.1):
        super().__init__(backbone_checkpoint_id=backbone_checkpoint_id, file_path=file_path)
        self.coreset_sampling_ratio = coreset_sampling_ratio


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
                anomaly_score=float(peak), uncertainty=float("nan"),  # unmeasured -> caller marks 'unknown'
            ))
    regions.sort(key=lambda r: r.anomaly_score, reverse=True)
    return regions[:max_regions]
