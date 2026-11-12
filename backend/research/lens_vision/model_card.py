"""Research model-card evidence writer.

Writes a self-describing JSON evidence record for a research run: reproducibility
config, source provenance, checkpoint licensing status, and the experimental
metrics — all explicitly marked RESEARCH ONLY. The card is written to a
caller-supplied path (tests use a temp dir); model-card evidence for real runs is
an operator artifact and is never committed to the repository.
"""
from __future__ import annotations

import json
from typing import Any

from research.lens_vision.checkpoint import get_record
from research.lens_vision.config import ResearchRunConfig

RESEARCH_ONLY_BANNER = (
    "RESEARCH ONLY — experimental. Not a clinically validated model. Not servable. "
    "Not clinically promotable. No clinical accuracy is claimed."
)


def build_model_card(config: ResearchRunConfig, result: dict[str, Any]) -> dict[str, Any]:
    checkpoint_license = "n/a"
    checkpoint_status = "none"
    try:
        rec = get_record(config.checkpoint_id) if config.checkpoint_id else None
        if rec is not None:
            checkpoint_license = rec.license
            checkpoint_status = "approved" if (rec.approved and rec.rights_cleared) else "blocked"
    except Exception:
        checkpoint_status = "unregistered"

    return {
        "banner": RESEARCH_ONLY_BANNER,
        "research_only": True,
        "clinical_promotion_eligible": False,
        "run": config.to_dict(),
        "config_fingerprint": config.fingerprint(),
        "checkpoint": {
            "id": config.checkpoint_id,
            "license": checkpoint_license,
            "status": checkpoint_status,
        },
        "source_provenance": {
            "class": config.source_provenance_class,
            "source_id": config.source_id,
            "tenant_id": config.tenant_id,
        },
        "result": result,
    }


def write_model_card(path: str, config: ResearchRunConfig, result: dict[str, Any]) -> dict[str, Any]:
    card = build_model_card(config, result)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(card, f, indent=2, sort_keys=True)
    return card
