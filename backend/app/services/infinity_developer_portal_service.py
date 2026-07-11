"""v5.0 — Project Infinity, Section 1: Developer Portal.

Composes the Developer Portal's supporting surfaces — API Explorer
catalog, rate-limit policy, and a per-developer dashboard summary. The
API Explorer catalog is a static, documented reference list mirroring the
real endpoints registered in `nexus_api_gateway.py` (never dynamically
introspected from the FastAPI app, which would create a routes<->service
circular import) — if a new `/api/v1/*` endpoint is added there, this
list must be updated alongside it. Rate limits are a fixed, documented
policy: no per-key request-counting infrastructure exists anywhere in
this codebase, so this never reports a fabricated live usage number.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services import infinity_developer_service, infinity_sandbox_service

API_EXPLORER_ENDPOINTS = [
    {"path": "/api/v1/identity", "system": "Identity"},
    {"path": "/api/v1/organizations", "system": "Organizations"},
    {"path": "/api/v1/users", "system": "Users"},
    {"path": "/api/v1/digital-twins", "system": "Digital Twins"},
    {"path": "/api/v1/knowledge", "system": "Knowledge Graph"},
    {"path": "/api/v1/instruments", "system": "Inspection"},
    {"path": "/api/v1/inspections", "system": "Inspection"},
    {"path": "/api/v1/analytics", "system": "Analytics"},
    {"path": "/api/v1/pulse", "system": "Pulse"},
    {"path": "/api/v1/sentinel", "system": "Sentinel"},
    {"path": "/api/v1/forge", "system": "Forge"},
    {"path": "/api/v1/catalyst", "system": "Catalyst"},
    {"path": "/api/v1/orbit", "system": "Orbit"},
    {"path": "/api/v1/apollo", "system": "Apollo"},
    {"path": "/api/v1/athena", "system": "Athena"},
    {"path": "/api/v1/phoenix", "system": "Phoenix"},
    {"path": "/api/v1/enterprise", "system": "Organizations"},
]

# A fixed, documented policy — not a live counter (no request-metering
# infrastructure exists anywhere in this codebase to back a real number).
RATE_LIMIT_POLICY = {
    "sandbox": {"requests_per_minute": 60, "requests_per_day": 5000},
    "certified_partner": {"requests_per_minute": 300, "requests_per_day": 100000},
    "note": "Fixed policy tiers — this platform has no live per-key request metering yet.",
}

TUTORIALS = [
    {"title": "Issue your first API key and call the sandbox gateway", "topic": "authentication"},
    {"title": "Build an AI Skill and submit it for certification", "topic": "ai_skills"},
    {"title": "Register a dashboard widget via the Plugin SDK", "topic": "plugin_sdk"},
    {"title": "Install an Application from the Marketplace", "topic": "marketplace"},
]


def api_explorer_catalog() -> list[dict]:
    return API_EXPLORER_ENDPOINTS


def rate_limit_policy() -> dict:
    return RATE_LIMIT_POLICY


def tutorials() -> list[dict]:
    return TUTORIALS


def developer_portal_summary(db: Session, developer_account_id: int) -> dict:
    account = infinity_developer_service.get_developer_account(db, developer_account_id)
    api_keys = infinity_developer_service.list_api_keys(db, developer_account_id)
    sandbox_sessions = infinity_sandbox_service.list_sandbox_sessions(db, developer_account_id)
    return {
        "account": account,
        "active_api_key_count": sum(1 for k in api_keys if not k["revoked"]),
        "sandbox_session_count": len(sandbox_sessions),
        "rate_limit_policy": RATE_LIMIT_POLICY["sandbox"] if account["sandbox_only"] else RATE_LIMIT_POLICY["certified_partner"],
        "api_explorer": API_EXPLORER_ENDPOINTS,
        "tutorials": TUTORIALS,
    }
