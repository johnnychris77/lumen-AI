"""Stage 5D — baseline-independence (§7) and clinical-safety invariants (§8).

Verifies that (a) anomaly localization is baseline-independent and a manufacturer
baseline can only enrich — never overwrite an anomaly or authorize release — and
(b) Stage 5D changes nothing in the production clinical path and an anomaly is
never a confirmed material/clinical condition.
"""
from __future__ import annotations

import pytest

# Init app layer before research imports (cold circular-import avoidance).
from app.db.session import SessionLocal  # noqa: F401

from research.lens_vision.anomaly_localization import StubLocalizer
from research.lens_vision.baseline_independence import (
    BaselineMisuseError,
    assert_baseline_not_authoritative,
    combine_with_baseline,
    standalone_capable,
)
from research.lens_vision.scientific_evidence import ScientificObservation


# ── §7 — baseline-independent capability ────────────────────────────────────

def test_localizer_is_standalone_without_baseline():
    assert standalone_capable(StubLocalizer()) is True


def test_baseline_is_enrichment_only_and_never_authoritative():
    anomaly = {"image_level_anomaly_score": 7.5, "research_only": True}
    # Image-only: no baseline needed.
    only = combine_with_baseline(anomaly, baseline_available=False)
    assert only["baseline_independent"] is True and only["manufacturer_baseline_used"] is False
    assert only["authorizes_release"] is False
    assert_baseline_not_authoritative(only)
    # With an approved baseline: advisory enrichment, anomaly preserved.
    enriched = combine_with_baseline(anomaly, baseline_available=True,
                                     baseline_comparison={"similarity": 0.9})
    assert enriched["manufacturer_baseline_used"] is True
    assert enriched["baseline_enrichment"]["role"] == "advisory_enrichment_only"
    assert enriched["anomaly_overwritten_by_baseline"] is False
    assert enriched["authorizes_release"] is False
    assert enriched["image_level_anomaly_score"] == 7.5           # anomaly unchanged
    assert_baseline_not_authoritative(enriched)


def test_baseline_misuse_is_rejected():
    bad = {"anomaly_overwritten_by_baseline": True}
    with pytest.raises(BaselineMisuseError):
        assert_baseline_not_authoritative(bad)
    with pytest.raises(BaselineMisuseError):
        assert_baseline_not_authoritative({"authorizes_release": True})


# ── §8 — clinical-safety invariants ─────────────────────────────────────────

def test_anomaly_is_never_a_confirmed_condition():
    # A scientific observation built from an AI anomaly carries NO clinical
    # disposition and NO confirmed diagnosis; identity stays None without lab proof.
    obs = ScientificObservation(ai_anomaly={"image_level_anomaly_score": 9.0})
    assert obs.clinical_disposition is None
    assert obs.confirmed_diagnosis is None
    assert obs.confirmed_material_identity is None
    assert obs.research_only is True and obs.clinical_promotion_eligible is False
    assert obs.human_review_required is True


def test_production_clinical_path_unchanged():
    # Stage 5D touches only research/; the live inference adapter still honestly
    # reports ai_unavailable (no model) and never fabricates an observation.
    from app.services.ml.live_inference_adapter import predict
    db = SessionLocal()
    try:
        res = predict(db, tenant_id="s5d-no-model", image_bytes=None)
        assert res["analysis_status"] == "ai_unavailable"
        assert res["observation"] is None
    finally:
        db.close()


def test_research_package_not_imported_by_app():
    # Defense in depth: no app module should import the research package.
    import importlib
    import app.services.ml.live_inference_adapter as lia
    mod = importlib.import_module(lia.__name__)
    assert "research" not in getattr(mod, "__dict__", {})
