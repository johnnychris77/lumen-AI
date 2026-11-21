"""P472-03 AW-07 — manufacturer identity is bound to a verified membership.

Before Batch 3, ``require_manufacturer_auth`` returned whatever ``X-Manufacturer-ID``
header the caller sent, so any authenticated user could assume any manufacturer /
repair-partner identity. The manufacturer identity is now resolved from an enabled
``ManufacturerMembership`` — exactly as the tenant identity is resolved from a
``TenantMembership``.

All identities and organizations here are synthetic. The requests use the shared
development token and name the acting user in ``x-lumenai-actor`` (the dev auth
context's ``actor``); the membership rows are seeded per-test.
"""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.db.models import ManufacturerMembership
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)
REFUSED = (401, 403)
PORTAL = "/api/manufacturer-portal/my-scorecard"


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def _user(memberships: dict[str, bool] | None = None) -> tuple[str, dict]:
    """A dev-token user acting as ``actor``, with the given {manufacturer_id: enabled}
    manufacturer memberships seeded."""
    actor = f"{_uid('aw07')}@example.com"
    db = SessionLocal()
    try:
        for manufacturer_id, enabled in (memberships or {}).items():
            db.add(ManufacturerMembership(
                manufacturer_id=manufacturer_id, user_email=actor,
                role="manufacturer_admin", is_enabled=enabled))
        db.commit()
    finally:
        db.close()
    return actor, {"Authorization": "Bearer dev-token", "x-lumenai-actor": actor}


def test_a_user_with_no_manufacturer_membership_cannot_assume_one():
    _, headers = _user()
    for claimed in ("stryker", "olympus", _uid("any")):
        r = client.get(PORTAL, headers={**headers, "X-Manufacturer-ID": claimed})
        assert r.status_code in REFUSED, f"served as {claimed}: HTTP {r.status_code} {r.text[:150]}"


def test_a_member_of_one_manufacturer_cannot_act_as_another():
    mine, theirs = _uid("mfr-a"), _uid("mfr-b")
    _, headers = _user({mine: True})
    r = client.get(PORTAL, headers={**headers, "X-Manufacturer-ID": theirs})
    assert r.status_code in REFUSED, f"cross-manufacturer access allowed: HTTP {r.status_code}"
    assert theirs not in r.text


def test_a_member_acts_in_their_manufacturer_when_naming_it():
    mine = _uid("mfr")
    _, headers = _user({mine: True})
    r = client.get(PORTAL, headers={**headers, "X-Manufacturer-ID": mine})
    assert r.status_code == 200, r.text
    assert r.json()["manufacturer_id"] == mine


def test_a_member_with_a_sole_membership_needs_no_header():
    mine = _uid("mfr")
    _, headers = _user({mine: True})
    r = client.get(PORTAL, headers=headers)  # no X-Manufacturer-ID
    assert r.status_code == 200, r.text
    assert r.json()["manufacturer_id"] == mine


def test_a_member_of_several_must_select_one():
    a, b = _uid("mfr-a"), _uid("mfr-b")
    _, headers = _user({a: True, b: True})
    # No header: ambiguous → refused.
    assert client.get(PORTAL, headers=headers).status_code in REFUSED
    # Naming one they belong to → served as that one.
    r = client.get(PORTAL, headers={**headers, "X-Manufacturer-ID": a})
    assert r.status_code == 200 and r.json()["manufacturer_id"] == a


def test_a_disabled_membership_is_no_membership():
    mine = _uid("mfr")
    _, headers = _user({mine: False})  # membership exists but is_enabled=False
    assert client.get(PORTAL, headers={**headers, "X-Manufacturer-ID": mine}).status_code in REFUSED
    assert client.get(PORTAL, headers=headers).status_code in REFUSED


def test_an_unauthenticated_caller_is_refused():
    assert client.get(PORTAL, headers={"X-Manufacturer-ID": _uid("mfr")}).status_code in REFUSED
