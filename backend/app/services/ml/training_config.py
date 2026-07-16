"""Genesis (Production Model Training, Scientific Validation & Model
Governance) — Section 2: reproducible training configuration.

A single, explicit, hashable record of every knob that affects a training
run's outcome. Two runs with the same config (and the same samples) must
produce identical results — see ``config_hash()`` and
``app.services.ml.candidate_training``'s reproducibility check.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

DEVICE_CPU = "cpu"  # the only device this pure-Python pipeline supports — never overclaimed as GPU


@dataclass(frozen=True)
class TrainingConfig:
    seed: int = 42
    optimizer: str = "batch_gradient_descent"
    learning_rate: float = 0.3
    scheduler: str = "constant"
    epochs: int = 500
    batch_size: int = 0  # 0 = full-batch (the only mode this pure-Python pipeline implements)
    augmentation: tuple[str, ...] = ("horizontal_flip", "brightness_jitter")
    input_resolution: tuple[int, int] = (300, 300)
    loss_function: str = "binary_cross_entropy_one_vs_rest"
    class_weighting: str = "balanced"
    early_stopping_patience: int = 0  # 0 = disabled (the pipeline always runs the full epoch count today)
    device: str = DEVICE_CPU

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["augmentation"] = list(self.augmentation)
        d["input_resolution"] = list(self.input_resolution)
        return d

    def config_hash(self) -> str:
        """Deterministic fingerprint of this configuration — used to prove
        two training runs used identical settings (Section 2's reproducibility
        requirement) without re-diffing every field by hand."""
        payload = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


def default_config(**overrides: Any) -> TrainingConfig:
    return TrainingConfig(**overrides)


def configs_match(a: TrainingConfig, b: TrainingConfig) -> bool:
    return a.config_hash() == b.config_hash()
