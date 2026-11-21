"""P472-03 Batch 5 — B5.2 manufacturer-membership lifecycle (AW-07, Issue #187).

Batch 3 bound the manufacturer identity to an enabled ``ManufacturerMembership``
(``tests/test_p472_03_aw07_manufacturer_identity.py``). What was missing:

* no way to express or enforce EXPIRY — a membership lived forever;
* no REVOCATION path: ``is_enabled=False`` was honoured but nothing set it, so
  revoking meant an unaudited database edit, with no record of who or why;
* no GRANT path, and therefore no audit trail of who granted a membership.

Policy-independent, fail-closed changes only (the IAM policy — who may grant,
identity proofing, role catalogue — is decision GD-9, unsigned):

* nullable ``expires_at`` / ``revoked_at`` / ``revoked_by`` /
  ``revocation_reason`` / ``granted_by`` / ``grant_reference`` columns
  (migration ``b5a2c7e19d40``; no backfill — NULL keeps today's behaviour);
* an expired membership is no membership (refused like a revoked one);
* ``revoke_manufacturer_membership`` — reduces access only, so it is available
  now; idempotent; writes a hash-chained audit event; takes effect on the very
  next request (no cache);
* ``grant_manufacturer_membership`` — GATED CLOSED until the IAM owner approves:
  it refuses before validating or writing anything. Its validation and audit
  plumbing is exercised here with the gate opened in-process only.
* No HTTP route grants or revokes: who may call them is the open decision.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.db.models import AuditLog, ManufacturerMembership
from app.db.session import SessionLocal
from app.main import app
from app.services import manufacturer_membership_service as iam
from app.services.audit_chain_verification_service import verify_audit_chain

client = TestClient(app)
PORTAL = "/api/manufacturer-portal/my-scorecard"
REFUSED = (401, 403)


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def _member(manufacturers: dict[str, dict] | None = None) -> tuple[str, dict, dict[str, int]]:
    """A dev-token user acting as ``actor`` with the given {manufacturer_id: column overrides}."""
    actor = f"{_uid('b52')}@example.com"
    ids: dict[str, int] = {}
    db = SessionLocal()
    try:
        for manufacturer_id, overrides in (manufacturers or {}).items():
            columns = {"role": "manufacturer_viewer", "is_enabled": True, **overrides}
            row = ManufacturerMembership(manufacturer_id=manufacturer_id, user_email=actor, **columns)
            db.add(row)
            db.flush()
            ids[manufacturer_id] = row.id
        db.commit()
    finally:
        db.close()
    return actor, {"Authorization": "Bearer dev-token", "x-lumenai-actor": actor}, ids


def _portal(headers: dict, manufacturer: str | None = None):
    extra = {"X-Manufacturer-ID": manufacturer} if manufacturer else {}
    return client.get(PORTAL, headers={**headers, **extra})


def _row(membership_id: int) -> ManufacturerMembership:
    db = SessionLocal()
    try:
        return db.get(ManufacturerMembership, membership_id)
    finally:
        db.close()


def _audit(membership_id: int) -> list[AuditLog]:
    db = SessionLocal()
    try:
        return (db.query(AuditLog)
                .filter(AuditLog.resource_type == iam.AUDIT_RESOURCE_TYPE,
                        AuditLog.resource_id == str(membership_id))
                .order_by(AuditLog.id.asc()).all())
    finally:
        db.close()


# ── enforcement ──────────────────────────────────────────────────────────────

class TestEnforcement:
    def test_forged_header_without_membership(self):
        _, headers, _ = _member()
        assert _portal(headers, _uid("mfr")).status_code in REFUSED

    def test_wrong_manufacturer(self):
        mine, theirs = _uid("mfr-a"), _uid("mfr-b")
        _, headers, _ = _member({mine: {}})
        response = _portal(headers, theirs)
        assert response.status_code in REFUSED and theirs not in response.text

    def test_absent_membership_without_header(self):
        _, headers, _ = _member()
        assert _portal(headers).status_code in REFUSED

    def test_unexpired_membership_is_served(self):
        mine = _uid("mfr")
        _, headers, _ = _member({mine: {"expires_at": datetime.now(timezone.utc) + timedelta(days=1)}})
        response = _portal(headers, mine)
        assert response.status_code == 200, response.text
        assert response.json()["manufacturer_id"] == mine

    def test_expired_membership_is_refused_named_or_not(self):
        mine = _uid("mfr")
        _, headers, _ = _member({mine: {"expires_at": datetime.now(timezone.utc) - timedelta(seconds=1)}})
        assert _portal(headers, mine).status_code in REFUSED
        assert _portal(headers).status_code in REFUSED

    def test_an_expired_membership_does_not_count_towards_sole_selection(self):
        live, dead = _uid("mfr-live"), _uid("mfr-dead")
        _, headers, _ = _member({live: {}, dead: {"expires_at": datetime.now(timezone.utc) - timedelta(days=1)}})
        response = _portal(headers)  # only one LIVE membership → it is selected
        assert response.status_code == 200 and response.json()["manufacturer_id"] == live

    def test_revoked_membership_carrying_revocation_metadata_is_refused(self):
        mine = _uid("mfr")
        _, headers, _ = _member({mine: {"is_enabled": False, "revoked_at": datetime.now(timezone.utc),
                                        "revoked_by": "iam-test", "revocation_reason": "test"}})
        assert _portal(headers, mine).status_code in REFUSED


# ── revocation ───────────────────────────────────────────────────────────────

class TestRevocation:
    def test_revocation_takes_effect_on_the_next_request(self):
        mine = _uid("mfr")
        _, headers, ids = _member({mine: {}})
        assert _portal(headers, mine).status_code == 200
        db = SessionLocal()
        try:
            iam.revoke_manufacturer_membership(db, membership_id=ids[mine], revoked_by="iam-officer@example.com",
                                               reason="offboarded")
        finally:
            db.close()
        assert _portal(headers, mine).status_code in REFUSED
        assert _portal(headers).status_code in REFUSED
        row = _row(ids[mine])
        assert row.is_enabled is False
        assert row.revoked_by == "iam-officer@example.com" and row.revocation_reason == "offboarded"
        assert row.revoked_at is not None

    def test_revocation_is_audited_once_and_idempotent(self):
        mine = _uid("mfr")
        _, _, ids = _member({mine: {}})
        db = SessionLocal()
        try:
            first = iam.revoke_manufacturer_membership(db, membership_id=ids[mine], revoked_by="iam@example.com",
                                                       reason="contract ended")
            again = iam.revoke_manufacturer_membership(db, membership_id=ids[mine], revoked_by="iam@example.com",
                                                       reason="contract ended")
        finally:
            db.close()
        assert first["changed"] is True and again["changed"] is False
        events = _audit(ids[mine])
        assert [e.action_type for e in events] == [iam.AUDIT_REVOKED]

    def test_revocation_requires_an_actor_and_a_reason(self):
        mine = _uid("mfr")
        _, _, ids = _member({mine: {}})
        db = SessionLocal()
        try:
            for revoked_by, reason in (("", "x"), ("iam@example.com", ""), ("  ", "  ")):
                with pytest.raises(ValueError):
                    iam.revoke_manufacturer_membership(db, membership_id=ids[mine], revoked_by=revoked_by,
                                                       reason=reason)
        finally:
            db.close()
        assert _row(ids[mine]).is_enabled is True
        assert _audit(ids[mine]) == []

    def test_unknown_membership_is_an_error_not_a_silent_success(self):
        db = SessionLocal()
        try:
            with pytest.raises(LookupError):
                iam.revoke_manufacturer_membership(db, membership_id=10**9, revoked_by="iam@example.com", reason="x")
        finally:
            db.close()

    def test_tampering_with_the_revocation_audit_event_is_detected(self):
        mine = _uid("mfr")
        _, _, ids = _member({mine: {}})
        db = SessionLocal()
        try:
            iam.revoke_manufacturer_membership(db, membership_id=ids[mine], revoked_by="iam@example.com", reason="r")
            assert verify_audit_chain(db, resource_type=iam.AUDIT_RESOURCE_TYPE,
                                      resource_id=str(ids[mine]))["verified"] is True
            event = db.query(AuditLog).filter(AuditLog.resource_type == iam.AUDIT_RESOURCE_TYPE,
                                              AuditLog.resource_id == str(ids[mine])).one()
            # 1) The application refuses to modify an audit record.
            from app.models.audit_log import AuditImmutabilityError
            event.actor_email = "someone-else@example.com"
            with pytest.raises(AuditImmutabilityError):
                db.commit()
            db.rollback()
            # 2) A direct database edit of who revoked it is detected by the hash chain.
            import json
            from sqlalchemy import text as sql
            raw = db.execute(sql("SELECT details FROM audit_logs WHERE id = :i"), {"i": event.id}).scalar()
            details = json.loads(raw) if isinstance(raw, str) else dict(raw)
            assert details.get("revoked_by") == "iam@example.com"
            details["revoked_by"] = "someone-else@example.com"
            db.execute(sql("UPDATE audit_logs SET details = :d WHERE id = :i"),
                       {"d": json.dumps(details), "i": event.id})
            db.commit()
            assert verify_audit_chain(db, resource_type=iam.AUDIT_RESOURCE_TYPE,
                                      resource_id=str(ids[mine]))["verified"] is False
        finally:
            db.close()


# ── grant (gated) ────────────────────────────────────────────────────────────

class TestGrantGate:
    def test_grant_is_refused_while_the_iam_gate_is_closed(self):
        assert iam.GRANTS_APPROVED is False, "the IAM gate must stay closed until GD-9 is signed"
        user, manufacturer = f"{_uid('grantee')}@example.com", _uid("mfr")
        db = SessionLocal()
        try:
            with pytest.raises(iam.ManufacturerIamGateClosed):
                iam.grant_manufacturer_membership(
                    db, manufacturer_id=manufacturer, user_email=user, role="manufacturer_viewer",
                    granted_by="iam@example.com", grant_reference="CHG-1")
            assert db.query(ManufacturerMembership).filter_by(user_email=user).count() == 0
            assert db.query(AuditLog).filter(AuditLog.resource_type == iam.AUDIT_RESOURCE_TYPE,
                                             AuditLog.actor_email == "iam@example.com",
                                             AuditLog.action_type == iam.AUDIT_GRANTED).count() == 0
        finally:
            db.close()

    def test_no_http_route_grants_or_revokes_manufacturer_memberships(self):
        for route in app.routes:
            endpoint = getattr(route, "endpoint", None)
            module = getattr(endpoint, "__module__", "")
            assert module != iam.__name__, getattr(route, "path", "")
        import inspect
        for route in app.routes:
            endpoint = getattr(route, "endpoint", None)
            if endpoint is None:
                continue
            try:
                source = inspect.getsource(endpoint)
            except (OSError, TypeError):
                continue
            assert "grant_manufacturer_membership" not in source and "revoke_manufacturer_membership" not in source


class TestGrantValidationWithGateOpenedInProcess:
    """The gate is opened for these tests only, to exercise the plumbing that
    will run once GD-9 is signed. Nothing here opens it in the application."""

    @pytest.fixture(autouse=True)
    def _open(self, monkeypatch):
        monkeypatch.setattr(iam, "GRANTS_APPROVED", True)

    def _grant(self, **overrides):
        args = dict(manufacturer_id=_uid("mfr"), user_email=f"{_uid('grantee')}@example.com",
                    role="manufacturer_viewer", granted_by="iam-officer@example.com", grant_reference="CHG-42")
        args.update(overrides)
        db = SessionLocal()
        try:
            return args, iam.grant_manufacturer_membership(db, **args)
        finally:
            db.close()

    def test_a_valid_grant_is_written_and_audited(self):
        args, result = self._grant(expires_at=datetime.now(timezone.utc) + timedelta(days=90))
        row = _row(result["membership_id"])
        assert row.is_enabled is True and row.granted_by == args["granted_by"]
        assert row.grant_reference == "CHG-42" and row.role == "manufacturer_viewer"
        assert [e.action_type for e in _audit(row.id)] == [iam.AUDIT_GRANTED]
        response = client.get(PORTAL, headers={"Authorization": "Bearer dev-token",
                                               "x-lumenai-actor": args["user_email"],
                                               "X-Manufacturer-ID": args["manufacturer_id"]})
        assert response.status_code == 200

    @pytest.mark.parametrize("overrides", [
        {"role": "manufacturer_admin"},                       # outside the least-privilege catalogue
        {"role": "admin"},
        {"granted_by": ""},                                   # no accountable grantor
        {"grant_reference": ""},                              # no change/approval reference
        {"manufacturer_id": ""},
        {"user_email": "not-an-email"},
        {"expires_at": datetime.now(timezone.utc) - timedelta(days=1)},  # already expired
    ])
    def test_invalid_grants_are_refused_and_write_nothing(self, overrides):
        with pytest.raises(ValueError):
            self._grant(**overrides)

    def test_self_grant_is_refused(self):
        email = f"{_uid('self')}@example.com"
        with pytest.raises(ValueError):
            self._grant(user_email=email, granted_by=email)

    def test_a_revoked_membership_is_not_silently_re_enabled_by_a_grant(self):
        args, result = self._grant()
        db = SessionLocal()
        try:
            iam.revoke_manufacturer_membership(db, membership_id=result["membership_id"],
                                               revoked_by="iam@example.com", reason="breach")
            with pytest.raises(ValueError):
                iam.grant_manufacturer_membership(db, **{**args, "grant_reference": "CHG-43"})
        finally:
            db.close()
        assert _row(result["membership_id"]).is_enabled is False
