"""v4.0 — LumenAI OS (Project Genesis), Section 2: Shared Intelligence
Layer.

## This is a facade, not a relocation

"Move shared intelligence into reusable services" does not mean deleting
and re-homing `digital_twin_engine.py`, `knowledge_graph_service.py`, or
any of the other engines below — every one of them already lives at a
stable import path and is already usable from any route file that
imports it. Actually moving nine mature engines (some with 15+ public
functions, thousands of call sites across eight prior sprints) in one
sprint would be a large, high-risk rewrite with no functional benefit:
Python modules are already globally importable, so "available to every
LumenAI application" was already true.

What Genesis adds is a single, documented **gateway module** — one
stable place every application module can import to discover which
shared engine backs which capability, without needing to know each
engine's home file. `get_shared_service(name)` returns the already-
imported module object for a named capability; nothing is copied,
wrapped, or re-implemented.
"""
from __future__ import annotations

from types import ModuleType

from app.services import (
    anatomy_risk_service,
    atlas_alert_service,
    beacon_repair_intelligence_service,
    capa_recommendation_service,
    digital_twin_engine,
    horizon_ai_improvement_service,
    insight_forecast_math,
    insight_recommendation_service,
    knowledge_graph_service,
    sentinel_engine_service,
    sentinel_recommendation_service,
)

# ── The nine named shared services (Section 2) ──────────────────────────────
SHARED_SERVICES: dict[str, ModuleType] = {
    "digital_twin_engine": digital_twin_engine,
    "knowledge_graph": knowledge_graph_service,
    "clinical_reasoning": knowledge_graph_service,  # reasoning_chain/explain_inspection live in the same Phase 21 engine
    "anatomy_engine": anatomy_risk_service,
    "spd_risk_engine": knowledge_graph_service,  # SPD risk scoring is embedded in the Phase 21 engine (no dedicated file exists)
    "forecast_engine": insight_forecast_math,
    "sentinel_engine": sentinel_engine_service,
}

# Multiple recommendation engines already exist, one per sprint — Genesis
# does not consolidate them into one implementation (each encodes
# sprint-specific domain logic), only registers all of them under one
# discoverable name so any new module can enumerate what's available.
RECOMMENDATION_ENGINES: dict[str, ModuleType] = {
    "sentinel": sentinel_recommendation_service,
    "insight": insight_recommendation_service,
    "horizon_ai_improvement": horizon_ai_improvement_service,
    "atlas_alerts": atlas_alert_service,
    "capa": capa_recommendation_service,
    "beacon_repair_intelligence": beacon_repair_intelligence_service,
}


class UnknownSharedServiceError(Exception):
    pass


def get_shared_service(name: str) -> ModuleType:
    if name not in SHARED_SERVICES:
        raise UnknownSharedServiceError(f"'{name}' is not a registered shared service. Known: {sorted(SHARED_SERVICES)}")
    return SHARED_SERVICES[name]


def get_recommendation_engine(name: str) -> ModuleType:
    if name not in RECOMMENDATION_ENGINES:
        raise UnknownSharedServiceError(f"'{name}' is not a registered recommendation engine. Known: {sorted(RECOMMENDATION_ENGINES)}")
    return RECOMMENDATION_ENGINES[name]


def list_shared_services() -> dict:
    return {
        "shared_services": {
            name: {"module": module.__name__, "doc": (module.__doc__ or "").strip().split("\n")[0]}
            for name, module in SHARED_SERVICES.items()
        },
        "recommendation_engines": {
            name: {"module": module.__name__, "doc": (module.__doc__ or "").strip().split("\n")[0]}
            for name, module in RECOMMENDATION_ENGINES.items()
        },
        "computer_vision_gateway": "app.cv.pipeline (CV inference pipeline: onnx_provider/mock_provider via app.cv.registry)",
    }
