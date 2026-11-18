"""P472-03 governance decisions GD-1 to GD-4 — what the code enforces.

``docs/enterprise-readiness/p472-03-security-governance-decisions.md`` records
four policies and which side of each the application now takes. None of them has
been signed off by its responsible owner; these tests pin the fail-closed
behaviour so that it cannot change without a visible decision.

* GD-1  operational counters require authentication            — enforced
* GD-2  audit verification is limited to the caller's tenant;
        there is no cross-tenant verification path             — enforced
* GD-3  vendor baselines are tenant-private                    — NOT implemented
        (a strict expected failure states the required behaviour)
* GD-4  ownerless CAPAs stay quarantined                       — enforced
"""
from __future__ import annotations

import sqlite3
import uuid

import pytest
from fastapi.testclient import TestClient

from app.db import models
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.audit_log import AuditLog
from app.models.user_role_assignment import UserRoleAssignment
from app.routers.auth_simple import _make_token

client = TestClient(app, raise_server_exceptions=False)
REFUSED = (401, 403)


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def _user(global_role: str, tenant: str | None = None, tenant_role: str = "tenant_admin") -> tuple[str, dict]:
    Base.metadata.create_all(bind=engine)
    email = f"{_uid('gd')}@example.com"
    db = SessionLocal()
    try:
        db.add(UserRoleAssignment(username=email, role=global_role, assigned_by="p472-03-governance"))
        if tenant:
            db.add(models.TenantMembership(tenant_id=tenant, user_email=email, role=tenant_role, is_enabled=True))
        db.commit()
    finally:
        db.close()
    return email, {"Authorization": f"Bearer {_make_token(email)}"}


@pytest.fixture
def tenants() -> tuple[str, str]:
    return _uid("gd-tenant-a"), _uid("gd-tenant-b")


# ══ GD-1 — operational counters require authentication ════════════════════════

COUNTERS = [
    "/api/network/participants/count",
    "/api/global-intelligence/network-stats",
    "/api/infrastructure/platform-stats",
]


class TestGd1CountersRequireAuthentication:
    @pytest.mark.parametrize("path", COUNTERS)
    def test_an_anonymous_caller_is_refused(self, path):
        response = client.get(path)
        assert response.status_code == 401
        assert not any(key in response.text for key in ("participant", "registered_instruments", "published_signals"))

    @pytest.mark.parametrize("path", COUNTERS)
    @pytest.mark.parametrize("authorization", ["Bearer not-a-token", "Bearer a.b.c", "Basic abc"])
    def test_an_invalid_token_is_refused(self, path, authorization):
        assert client.get(path, headers={"Authorization": authorization}).status_code == 401

    @pytest.mark.parametrize("path", COUNTERS)
    def test_a_user_with_no_tenant_membership_is_refused(self, path):
        _, headers = _user("spd_manager")
        assert client.get(path, headers=headers).status_code == 403

    @pytest.mark.parametrize("path", COUNTERS)
    def test_a_verified_member_is_served(self, path, tenants):
        _, headers = _user("viewer", tenants[0], "viewer")
        assert client.get(path, headers=headers).status_code == 200


# ══ GD-2 — audit verification stays inside the caller's tenant ════════════════

_SAME = object()


def _event(tenant: str, resource_id: str, *, resource_type: str = "gd2_resource", stamped=_SAME) -> int:
    """One hash-chained audit event of ``tenant`` on a resource, written by the real
    writer. ``stamped`` overrides the tenant column, to reproduce events that older
    code wrote with no owner (audit rows are immutable, so it cannot be edited in)."""
    from app.auth.context import build_dev_auth_context
    from app.services.enterprise_audit_service import record_enterprise_audit_event

    db = SessionLocal()
    try:
        context = build_dev_auth_context(actor=f"actor@{tenant}", role="hospital_admin",
                                         tenant_id=tenant, tenant_name=tenant)
        row = record_enterprise_audit_event(
            db, action_type="gd2_test_event", resource_type=resource_type, resource_id=resource_id,
            actor=context.actor, actor_role=context.role, auth_context=context,
            details={"note": f"private to {tenant}"},
            **({} if stamped is _SAME else {"tenant_id": stamped}))
        return row.id
    finally:
        db.close()


def _verify_chain(headers: dict, resource_id: str):
    return client.get("/api/enterprise/audit/verify-chain", headers=headers,
                      params={"resource_type": "gd2_resource", "resource_id": resource_id})


class TestGd2ChainVerification:
    def test_an_administrator_verifies_their_own_tenants_chain(self, tenants):
        a, _ = tenants
        resource = _uid("res")
        _event(a, resource)
        _event(a, resource)
        _, admin = _user("hospital_admin", a)
        response = _verify_chain(admin, resource)
        assert response.status_code == 200, response.text
        assert response.json()["verified"] is True and response.json()["event_count"] == 2

    def test_another_tenants_chain_looks_exactly_like_no_chain(self, tenants):
        a, b = tenants
        theirs, nothing = _uid("res"), _uid("res")
        _event(b, theirs)
        _event(b, theirs)
        _, admin = _user("hospital_admin", a)

        seen, missing = _verify_chain(admin, theirs), _verify_chain(admin, nothing)

        assert seen.status_code == missing.status_code == 200
        strip = lambda body: {k: v for k, v in body.items() if k != "resource_id"}  # noqa: E731
        assert strip(seen.json()) == strip(missing.json())
        assert seen.json()["event_count"] == 0 and b not in seen.text

    @pytest.mark.parametrize("other", ["tenant-b", "default-tenant", ""], ids=["another-tenant", "default-tenant", "no-tenant"])
    def test_a_chain_that_leaves_the_callers_tenant_is_not_verified(self, tenants, other):
        a, b = tenants
        resource = _uid("res")
        _event(a, resource)
        if other == "tenant-b":
            _event(b, resource)
        else:
            event_id = _event(a, resource, stamped=other)          # an event written without an owner
            db = SessionLocal()
            try:
                assert db.get(AuditLog, event_id).tenant_id != a
            finally:
                db.close()
        _, admin = _user("hospital_admin", a)

        response = _verify_chain(admin, resource)

        assert response.status_code == 403
        assert "event_count" not in response.text and b not in response.text

    def test_there_is_no_cross_tenant_verification_for_any_role(self, tenants):
        """Not for an enterprise administrator, and not for the platform administrator."""
        a, b = tenants
        resource = _uid("res")
        _event(b, resource)
        for role in ("enterprise_admin", "hospital_admin", "admin"):
            _, headers = _user(role, a)
            for extra in ({}, {"X-Tenant-Id": b}, {"X-LumenAI-Tenant-Id": b}):
                response = _verify_chain({**headers, **extra}, resource)
                assert response.status_code in REFUSED or response.json().get("event_count") == 0, (role, extra)
                assert b not in response.text or response.status_code in REFUSED


class TestGd2HashVerification:
    @pytest.fixture
    def export(self, tenants):
        """Tenant B produces an audit export and an evidence bundle."""
        _, b = tenants
        _event(b, _uid("res"))
        _, admin_b = _user("hospital_admin", b)
        exported = client.get("/api/enterprise/audit/events/export.csv", headers=admin_b)
        assert exported.status_code == 200, exported.text[:300]
        bundle = client.get("/api/enterprise/audit/evidence-bundle", headers=admin_b)
        assert bundle.status_code == 200, bundle.text[:300]
        return {
            "admin_b": admin_b,
            "checks": [
                ("/api/enterprise/audit/events/export/verify",
                 {"audit_export_hash": exported.headers["X-LumenAI-Audit-Export-Hash"]}),
                ("/api/enterprise/audit/events/export/manifest/verify",
                 {"manifest_hash": exported.headers["X-LumenAI-Audit-Manifest-Hash"]}),
                ("/api/enterprise/audit/evidence-bundle/verify", {"bundle_hash": bundle.json()["bundle_hash"]}),
                ("/api/enterprise/audit/evidence-bundle/verification-summary",
                 {"bundle_hash": bundle.json()["bundle_hash"]}),
            ],
        }

    def test_the_owner_verifies_their_own_exports_and_bundles(self, export):
        for path, params in export["checks"]:
            response = client.get(path, headers=export["admin_b"], params=params)
            assert response.status_code == 200 and response.json()["verified"] is True, (path, response.text[:200])

    def test_another_tenants_administrator_cannot_confirm_them(self, tenants, export):
        a, b = tenants
        _, admin_a = _user("hospital_admin", a)
        for path, params in export["checks"]:
            response = client.get(path, headers=admin_a, params=params)
            assert response.status_code == 200, (path, response.status_code)
            body = response.json()
            assert body["verified"] is False, f"{path}: tenant A confirmed tenant B's export"
            assert body.get("event_id") is None and b not in response.text
            assert not ({"filters", "manifest", "bundle", "filename", "export_count"} & set(body)), path


# ══ GD-3 — vendor baselines are tenant-private (ENFORCED) ════════════════════
#
# GD-3 is now implemented: ``EnterpriseVendorBaselineSubscription`` and
# ``VendorBaselineAuditEvent`` carry a ``tenant_id`` stamped from the verified
# tenant of the submitting request, and every list/approve/match/audit/scoring
# read is scoped to the caller's tenant. A baseline owned by another tenant (or
# an unattributed pre-GD-3 row with tenant_id IS NULL) is invisible and behaves
# exactly like a non-existent record. The authorized cross-tenant sharing path
# GD-3 anticipates is deliberately NOT built; these tests pin the private
# default so it cannot regress without a visible decision.


def _seed_vendor_baseline(
    tenant_id: str | None,
    *,
    marker: str,
    instrument_category: str = "",
    approval_status: str = "pending_hospital_review",
    baseline_status: str = "vendor_submitted",
    baseline_source: str = "vendor",
    with_audit_event: bool = False,
) -> int:
    from app.models.enterprise_quality import EnterpriseVendorBaselineSubscription
    from app.services.vendor_baseline_audit_service import log_vendor_baseline_audit_event

    db = SessionLocal()
    try:
        row = EnterpriseVendorBaselineSubscription(
            tenant_id=tenant_id,
            vendor_name=f"vendor-{marker}",
            instrument_name=marker,
            instrument_category=instrument_category or marker,
            approval_status=approval_status,
            baseline_status=baseline_status,
            baseline_source=baseline_source,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        baseline_id = row.id
        if with_audit_event:
            log_vendor_baseline_audit_event(
                db=db,
                baseline_id=baseline_id,
                tenant_id=tenant_id,
                event_type="baseline_submitted",
                notes=marker,
                new_status="pending_hospital_review",
            )
            db.commit()
        return baseline_id
    finally:
        db.close()


def _baseline_row(baseline_id: int):
    from app.models.enterprise_quality import EnterpriseVendorBaselineSubscription

    db = SessionLocal()
    try:
        return db.get(EnterpriseVendorBaselineSubscription, baseline_id)
    finally:
        db.close()


class TestGd3VendorBaselinesAreTenantPrivate:
    def test_a_baseline_submitted_in_one_tenant_is_not_listed_in_another(self, tenants):
        a, b = tenants
        marker = _uid("gd3-baseline")
        _seed_vendor_baseline(b, marker=marker)

        _, admin_a = _user("hospital_admin", a)
        _, admin_b = _user("hospital_admin", b)

        path = "/api/enterprise/vendor-baseline-subscription/baselines"
        seen_by_a = client.get(path, headers=admin_a)
        seen_by_b = client.get(path, headers=admin_b)

        assert seen_by_a.status_code == 200 and seen_by_b.status_code == 200
        assert marker not in seen_by_a.text, "tenant A sees tenant B's vendor baseline"
        # It is owned, not globally hidden: its own tenant still sees it.
        assert marker in seen_by_b.text, "tenant B cannot see its own vendor baseline"

    def test_a_tenant_cannot_approve_another_tenants_baseline(self, tenants):
        a, b = tenants
        marker = _uid("gd3-approve")
        baseline_id = _seed_vendor_baseline(b, marker=marker)

        _, admin_a = _user("hospital_admin", a)
        approve = client.post(
            f"/api/enterprise/vendor-baseline-subscription/baselines/{baseline_id}/approve",
            headers=admin_a,
            json={},
        )
        # A foreign baseline id is indistinguishable from a missing one.
        assert approve.status_code == 200 and approve.json()["status"] == "not_found"
        # The record was not mutated by the foreign tenant.
        row = _baseline_row(baseline_id)
        assert row is not None and row.approval_status == "pending_hospital_review"
        assert row.approved_by in (None, "")

        # The owning tenant can approve it.
        _, admin_b = _user("hospital_admin", b)
        ok = client.post(
            f"/api/enterprise/vendor-baseline-subscription/baselines/{baseline_id}/approve",
            headers=admin_b,
            json={},
        )
        assert ok.status_code == 200 and ok.json()["status"] == "success"
        assert _baseline_row(baseline_id).approval_status == "hospital_approved"

    def test_a_tenant_cannot_read_another_tenants_baseline_audit_trail(self, tenants):
        a, b = tenants
        marker = _uid("gd3-audit")
        baseline_id = _seed_vendor_baseline(b, marker=marker, with_audit_event=True)

        _, admin_a = _user("hospital_admin", a)
        _, admin_b = _user("hospital_admin", b)

        path = f"/api/enterprise/vendor-baseline-subscription/baselines/{baseline_id}/audit"
        foreign = client.get(path, headers=admin_a)
        owner = client.get(path, headers=admin_b)

        assert foreign.status_code == 404, foreign.text[:200]
        assert owner.status_code == 200 and marker in owner.text

    def test_scoring_only_resolves_the_callers_own_tenant_baseline(self, tenants):
        """The clinical-quality leak: an approved baseline owned by tenant B must
        never drive tenant A's scoring, and an unattributed row drives nobody's."""
        from app.services.baseline_comparison_scoring_service import resolve_baseline

        a, b = tenants
        itype = _uid("gd3-scoretype")
        _seed_vendor_baseline(
            b, marker=_uid("gd3-score"), instrument_category=itype,
            approval_status="approved", baseline_status="approved", baseline_source="manufacturer",
        )

        db = SessionLocal()
        try:
            for_a = resolve_baseline(db, itype, a)
            for_b = resolve_baseline(db, itype, b)
        finally:
            db.close()

        assert for_a["baseline_found"] is False, "tenant B's baseline drove tenant A's scoring"
        assert for_b["baseline_found"] is True, "tenant B could not use its own baseline for scoring"

    def test_an_unattributed_baseline_is_visible_to_no_tenant(self, tenants):
        """Fail-closed: rows written before GD-3 (tenant_id IS NULL) are quarantined
        until the baseline workflow owner attributes them — visible to no tenant
        and usable by no tenant's scoring."""
        from app.services.baseline_comparison_scoring_service import resolve_baseline

        a, b = tenants
        marker = _uid("gd3-orphan")
        itype = _uid("gd3-orphantype")
        _seed_vendor_baseline(
            None, marker=marker, instrument_category=itype,
            approval_status="approved", baseline_status="approved", baseline_source="manufacturer",
        )

        _, admin_a = _user("hospital_admin", a)
        _, admin_b = _user("hospital_admin", b)
        path = "/api/enterprise/vendor-baseline-subscription/baselines"
        assert marker not in client.get(path, headers=admin_a).text
        assert marker not in client.get(path, headers=admin_b).text

        db = SessionLocal()
        try:
            assert resolve_baseline(db, itype, a)["baseline_found"] is False
            assert resolve_baseline(db, itype, b)["baseline_found"] is False
        finally:
            db.close()


# ══ GD-4 — ownerless CAPAs stay quarantined ═══════════════════════════════════

class TestGd4OwnerlessCapasAreQuarantined:
    @pytest.fixture
    def ownerless(self):
        from app.services import capa_service

        capa_service.init_capa_db()
        capa_id, title = _uid("capa"), _uid("ownerless-capa-title")
        with sqlite3.connect(capa_service.DB_PATH) as connection:
            columns = [row[1] for row in connection.execute("PRAGMA table_info(capas)")]
            values = {"id": capa_id, "title": title, "source": "legacy", "description": "", "risk_level": "medium",
                      "owner": "Quality", "status": "open", "tenant_id": None,
                      "created_at": "2026-01-01T00:00:00+00:00", "updated_at": "2026-01-01T00:00:00+00:00"}
            names = [name for name in values if name in columns]
            connection.execute(
                f"INSERT INTO capas ({', '.join(names)}) VALUES ({', '.join('?' for _ in names)})",
                [values[name] for name in names])
        return capa_id, title

    @staticmethod
    def _stored(capa_id: str):
        from app.services import capa_service

        with sqlite3.connect(capa_service.DB_PATH) as connection:
            return connection.execute("SELECT status, tenant_id FROM capas WHERE id = ?", (capa_id,)).fetchone()

    def test_no_tenant_sees_reads_or_changes_an_ownerless_capa(self, ownerless, tenants):
        capa_id, title = ownerless
        for tenant in tenants:
            _, headers = _user("spd_manager", tenant)
            for path in ("/api/capa", "/api/capa/summary", "/api/capa/powerbi-csv", "/api/capa/escalations"):
                response = client.get(path, headers=headers)
                assert title not in response.text and capa_id not in response.text, path
            assert client.get(f"/api/capa/{capa_id}", headers=headers).status_code == 404
            changed = client.patch(f"/api/capa/{capa_id}", headers=headers, json={"status": "closed"})
            assert changed.status_code in (404, 405, 422)
        assert self._stored(capa_id) == ("open", None)          # still there, still unowned, unchanged

    def test_the_service_has_no_all_tenants_mode(self, ownerless):
        from app.services import capa_service

        capa_id, _ = ownerless
        for call in (lambda: capa_service.list_capas(tenant_id=""), lambda: capa_service.get_capa(capa_id, tenant_id=""),
                     lambda: capa_service.capa_summary(tenant_id=None)):
            with pytest.raises(ValueError):
                call()
        with pytest.raises(TypeError):
            capa_service.list_capas()                            # the tenant is not optional
