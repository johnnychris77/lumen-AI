"""Image embedding extractors for the research benchmark.

Two providers, one interface (``embed(image_bytes) -> list[float]``):

* ``StubEmbedder`` — a deterministic, Pillow-only feature extractor for CPU
  pipeline **smoke tests**. It is NOT a learned model and produces NO scientific
  embeddings; it exists so the pipeline can be exercised and tested end-to-end
  without PyTorch, a GPU, or any downloaded weights.
* ``Dinov2Embedder`` — the real frozen DINOv2 backbone. It requires PyTorch and an
  explicitly-approved, rights-cleared, hash-verified checkpoint. In an
  environment without torch/approved weights it raises a clear, governed error
  (the documented Stage 5A blocker) rather than silently falling back.

Neither path ever downloads weights automatically.
"""
from __future__ import annotations

from research.lens_vision.checkpoint import verify_checkpoint
from research.lens_vision.deps import require_torch
from research.lens_vision.images import decode_rgb

STUB_EMBED_GRID = 4          # 4x4 cells
STUB_EMBED_DIM = STUB_EMBED_GRID * STUB_EMBED_GRID * 3  # per-cell mean R,G,B


class Embedder:
    name: str = "base"

    def embed(self, image_bytes: bytes | None) -> list[float]:  # pragma: no cover - interface
        raise NotImplementedError

    def embed_many(self, images: list[bytes | None]) -> list[list[float]]:
        return [self.embed(b) for b in images]


class StubEmbedder(Embedder):
    """Deterministic grid-mean embedding (smoke tests only — NOT scientific)."""

    name = "smoke_stub"

    def __init__(self, *, grid: int = STUB_EMBED_GRID, size: tuple[int, int] = (96, 96)):
        self.grid = grid
        self.size = size

    def embed(self, image_bytes: bytes | None) -> list[float]:
        img = decode_rgb(image_bytes, size=self.size)
        w, h = img.size
        px = img.load()
        cell_w = max(1, w // self.grid)
        cell_h = max(1, h // self.grid)
        vec: list[float] = []
        for gy in range(self.grid):
            for gx in range(self.grid):
                r = g = b = 0
                count = 0
                for y in range(gy * cell_h, min((gy + 1) * cell_h, h)):
                    for x in range(gx * cell_w, min((gx + 1) * cell_w, w)):
                        pr, pg, pb = px[x, y]
                        r += pr
                        g += pg
                        b += pb
                        count += 1
                count = count or 1
                vec.extend([r / count / 255.0, g / count / 255.0, b / count / 255.0])
        return vec


class ArchitectureMismatchError(RuntimeError):
    """The loaded model's architecture does not match the checkpoint's declared
    architecture — a checkpoint/architecture compatibility violation."""


class Dinov2Embedder(Embedder):
    """Frozen DINOv2 backbone. Requires torch + an approved, verified checkpoint.

    Import-safe without torch; torch is imported only when an instance is actually
    constructed, and only after the checkpoint passes governance verification.
    A real benchmark therefore requires, by construction:
      * an explicitly approved, rights-cleared, hash-VERIFIED checkpoint;
      * checkpoint/architecture COMPATIBILITY (the loaded model must report the
        checkpoint's declared architecture);
      * the checkpoint-SPECIFIC preprocessing/normalization (from the record);
      * evaluation mode + disabled gradients;
      * deterministic behaviour where the backend supports it;
      * a recorded checkpoint digest + architecture (``self.digest`` /
        ``self.architecture``) for the model card.
    Automatic weight download is deliberately not implemented.
    """

    name = "dinov2"

    def __init__(self, *, checkpoint_id: str, file_path: str | None = None, model_loader=None, seed: int = 1337):
        # Governance first: refuse unless approved + rights-cleared + hash-verified.
        self.record = verify_checkpoint(checkpoint_id, file_path=file_path)
        self.checkpoint_id = checkpoint_id
        self.architecture = self.record.architecture
        self.preprocessing = self.record.preprocessing or {}
        self.digest = self.record.expected_sha256
        require_torch()  # raises ResearchDependencyMissing when torch is absent
        if not self.architecture or not self.preprocessing:
            raise ArchitectureMismatchError(
                f"Checkpoint '{checkpoint_id}' has no declared architecture/preprocessing; "
                "a real embedding run requires both."
            )
        if model_loader is None:
            raise NotImplementedError(
                "A model_loader(file_path)->(model, architecture) must be supplied to load "
                "approved DINOv2 weights in an isolated research environment. Automatic "
                "download is deliberately not implemented."
            )
        import torch  # noqa: PLC0415

        # Determinism where supported (guarded — some ops have no deterministic impl).
        torch.manual_seed(seed)
        try:
            torch.use_deterministic_algorithms(True, warn_only=True)
        except (RuntimeError, AttributeError):
            pass

        model, loaded_arch = model_loader(file_path)
        if loaded_arch != self.architecture:
            raise ArchitectureMismatchError(
                f"Loaded model architecture '{loaded_arch}' does not match checkpoint "
                f"'{checkpoint_id}' declared architecture '{self.architecture}'."
            )
        model.eval()  # evaluation mode — no dropout/batchnorm updates
        self._model = model

    def _transform(self, image_bytes: bytes | None):  # pragma: no cover - needs torch
        import numpy as np  # noqa: PLC0415
        import torch  # noqa: PLC0415

        size = tuple(self.preprocessing.get("resize", [224, 224]))
        img = decode_rgb(image_bytes, size=size)
        arr = np.asarray(img, dtype="float32") / 255.0
        mean = np.asarray(self.preprocessing.get("mean", [0.0, 0.0, 0.0]), dtype="float32")
        std = np.asarray(self.preprocessing.get("std", [1.0, 1.0, 1.0]), dtype="float32")
        arr = (arr - mean) / std
        return torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)

    def embed(self, image_bytes: bytes | None) -> list[float]:  # pragma: no cover - needs torch
        import torch  # noqa: PLC0415

        tensor = self._transform(image_bytes)
        with torch.no_grad():  # disabled gradient computation
            out = self._model(tensor)
        return out.flatten().tolist()
