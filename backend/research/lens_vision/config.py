"""Reproducible research-run configuration.

Captures everything needed to reproduce a research experiment: random seed, code
revision, framework versions, the explicitly-approved checkpoint identity, and
the source provenance of the data. Serializes to a stable fingerprint recorded in
the model-card evidence. No weights, datasets, patient images, or secrets are
ever stored here.
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

from research.lens_vision.deps import torch_available


def code_revision() -> str:
    """Current git revision, or 'unknown' when git is unavailable."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def framework_versions() -> dict[str, str]:
    """Versions of the frameworks in play (torch only when installed)."""
    versions = {"python": sys.version.split()[0], "platform": platform.platform()}
    try:
        import PIL  # noqa: PLC0415
        versions["pillow"] = getattr(PIL, "__version__", "unknown")
    except ImportError:
        pass
    if torch_available():
        try:
            import torch  # noqa: PLC0415
            versions["torch"] = torch.__version__
        except ImportError:
            pass
    return versions


@dataclass
class ResearchRunConfig:
    """A single research experiment's reproducibility record."""

    run_id: str
    seed: int = 1337
    # The explicitly-approved checkpoint this run is allowed to load (empty when
    # using the deterministic stub for a pipeline smoke test).
    checkpoint_id: str = ""
    checkpoint_sha256: str = ""
    # Source provenance of the data used (a Stage 4 provenance class + source id).
    source_provenance_class: str = ""
    source_id: str = ""
    tenant_id: str = ""
    embedder: str = "smoke_stub"
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        d = asdict(self)
        d["code_revision"] = code_revision()
        d["framework_versions"] = framework_versions()
        d["research_only"] = True
        return d

    def fingerprint(self) -> str:
        """Stable SHA-256 over the reproducibility-relevant fields (excludes the
        wall-clock timestamp), so an identical config reproduces an identical id."""
        core = {
            "run_id": self.run_id, "seed": self.seed, "checkpoint_id": self.checkpoint_id,
            "checkpoint_sha256": self.checkpoint_sha256,
            "source_provenance_class": self.source_provenance_class,
            "source_id": self.source_id, "embedder": self.embedder,
            "code_revision": code_revision(),
        }
        blob = json.dumps(core, sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()
