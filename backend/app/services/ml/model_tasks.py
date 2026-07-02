"""Phase 17 §3 — Model task definitions.

The label spaces for each anatomy-aware classifier LumenAI intends to train.
Kept as data so training, evaluation, and the registry all agree on the classes.
These mirror the instrument-anatomy library and the SPD scoring vocabulary.
"""
from __future__ import annotations

# A. Instrument Family Classifier
INSTRUMENT_FAMILY_LABELS = [
    "rigid_scope", "flexible_endoscope", "drill_bit", "kerrison_rongeur",
    "scissors", "needle_holder", "laparoscopic", "general_forceps", "unknown",
]

# B. Anatomy Zone Classifier
ANATOMY_ZONE_LABELS = [
    "o-ring area", "serration", "groove", "hinge", "box lock", "drill-bit flute",
    "threaded region", "lumen", "scope port", "cutting edge", "insulation edge",
    "handle seam", "unknown",
]

# C. Finding Classifier
FINDING_LABELS = [
    "blood", "bone", "tissue", "organic residue", "debris", "rust", "corrosion",
    "discoloration", "crack", "pitting", "insulation damage", "missing component",
    "wear", "none",
]

# D. Severity Classifier
SEVERITY_LABELS = ["none", "trace", "minor", "moderate", "visible", "severe", "heavy"]

# E. Clinical Disposition Classifier
DISPOSITION_LABELS = ["pass", "monitor", "supervisor_review", "reprocess", "remove_from_service"]


# Task registry: task_key → (human name, label space, whether safety-critical).
MODEL_TASKS: dict[str, dict] = {
    "instrument_family": {
        "name": "Instrument Family Classifier",
        "labels": INSTRUMENT_FAMILY_LABELS,
        "safety_critical": False,
    },
    "anatomy_zone": {
        "name": "Anatomy Zone Classifier",
        "labels": ANATOMY_ZONE_LABELS,
        "safety_critical": False,
    },
    "finding": {
        "name": "Finding Classifier",
        "labels": FINDING_LABELS,
        "safety_critical": True,
    },
    "severity": {
        "name": "Severity Classifier",
        "labels": SEVERITY_LABELS,
        "safety_critical": True,
    },
    "clinical_disposition": {
        "name": "Clinical Disposition Classifier",
        "labels": DISPOSITION_LABELS,
        "safety_critical": True,
    },
}

# Findings whose *false negatives* are the most dangerous (missed contamination or
# structural failure). Tracked explicitly as safety metrics (§6).
SAFETY_CRITICAL_FINDINGS = [
    "blood", "tissue", "organic residue", "crack", "missing component",
]


def task_labels(task_key: str) -> list[str]:
    if task_key not in MODEL_TASKS:
        raise KeyError(f"Unknown model task '{task_key}'. Known: {sorted(MODEL_TASKS)}")
    return list(MODEL_TASKS[task_key]["labels"])


def is_valid_task(task_key: str) -> bool:
    return task_key in MODEL_TASKS
