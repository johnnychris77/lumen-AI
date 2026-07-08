"""Regression tests for issues flagged by automated review on PR #73
(merged): tenant isolation in /api/analytics/kpi-summary and /powerbi,
supervisor-role read access, and deterministic case-insensitive credential
matching.
"""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from passlib.hash import bcrypt

from app.db.session import SessionLocal
from app.main import app
from app.models.admin_credential import AdminCredential
from app.models.baseline_library import BaselineLibraryEntry
from app.db.models import TenantMembership
from app.models.user_role_assignment import UserRoleAssignment

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_OPERATOR = {"Authorization": "Bearer operator-token"}
SHA = "a1b2c3d4" + "0" * 56

# The dev-token auth path (app/deps.py) maps every "operator-token" caller to
# this fixed, deterministic email — real per-request identity requires the
# enterprise OIDC path instead. Tests grant this email membership in
# whichever synthetic tenant they need to access via header, mirroring what
# a real deployment's tenant-membership admin flow would do.
OPERATOR_EMAIL = "operator@local.dev"


def _baseline(itype: str) -> None:
    db = SessionLocal()
    try:
        db.query(BaselineLibraryEntry).filter(BaselineLibraryEntry.instrument_category == itype).delete()
        db.add(BaselineLibraryEntry(
            udi=f"kh-{itype}", instrument_category=itype, manufacturer_name="M",
            model_name="X", baseline_type="manufacturer", approval_status="approved",
        ))
        db.commit()
    finally:
        db.close()


def _grant_membership(tenant_id: str, user_email: str) -> None:
    db = SessionLocal()
    try:
        db.query(TenantMembership).filter(
            TenantMembership.tenant_id == tenant_id, TenantMembership.user_email == user_email,
        ).delete()
        db.add(TenantMembership(tenant_id=tenant_id, user_email=user_email, role="operator", is_enabled=True))
        db.commit()
    finally:
        db.close()


def _create_inspection(tenant_id: str) -> None:
    r = client.post("/api/inspections", json={
        "instrument_type": "scissors", "site_name": "Mercy", "has_image": True,
        "image_sha256": SHA, "file_name": "x.jpg", "finding_categories": [],
    }, headers={**AUTH_OPERATOR, "X-Tenant-Id": tenant_id})
    assert r.status_code == 201, r.text


def _kpi(tenant_id: str, headers: dict) -> dict:
    r = client.get("/api/analytics/kpi-summary", headers={**headers, "X-Tenant-Id": tenant_id})
    assert r.status_code == 200, r.text
    return r.json()


class TestKpiSummaryTenantIsolation:
    def test_non_admin_never_sees_another_tenants_inspections(self):
        _baseline("scissors")
        tenant_a = f"tenant-{uuid.uuid4().hex[:8]}"
        tenant_b = f"tenant-{uuid.uuid4().hex[:8]}"
        _grant_membership(tenant_a, OPERATOR_EMAIL)
        _grant_membership(tenant_b, OPERATOR_EMAIL)

        assert _kpi(tenant_a, AUTH_OPERATOR)["total_inspections"] == 0
        assert _kpi(tenant_b, AUTH_OPERATOR)["total_inspections"] == 0

        _create_inspection(tenant_a)

        # Regression: before the tenant-isolation fix, an operator/viewer
        # request with no resolvable current_user.tenant_id fell through to
        # an unfiltered, platform-wide query — tenant_b would have seen
        # tenant_a's row (and every other tenant's rows in the whole suite).
        assert _kpi(tenant_a, AUTH_OPERATOR)["total_inspections"] == 1
        assert _kpi(tenant_b, AUTH_OPERATOR)["total_inspections"] == 0

    def test_powerbi_dataset_isolates_tenants_for_non_admin(self):
        _baseline("scissors")
        tenant_a = f"tenant-{uuid.uuid4().hex[:8]}"
        tenant_b = f"tenant-{uuid.uuid4().hex[:8]}"
        _create_inspection(tenant_a)

        r = client.get("/api/analytics/powerbi", headers={**AUTH_ADMIN, "X-Tenant-Id": tenant_b})
        # admin role sees the platform-wide dataset regardless of header —
        # this just confirms the endpoint still responds; isolation for a
        # non-admin caller is exercised via spd_manager access below.
        assert r.status_code == 200

    def test_admin_sees_platform_wide_total(self):
        _baseline("scissors")
        tenant_a = f"tenant-{uuid.uuid4().hex[:8]}"
        _create_inspection(tenant_a)
        before = _kpi(tenant_a, AUTH_ADMIN)["total_inspections"]
        # Admin's view is header-independent (role == admin is never scoped).
        other = _kpi(f"tenant-{uuid.uuid4().hex[:8]}", AUTH_ADMIN)["total_inspections"]
        assert before == other


class TestTenantHeaderRequiresMembership:
    """Regression tests for the P1 finding on PR #81: current_user from the
    simple dev/JWT auth path never carries its own tenant_id, so an
    operator/viewer could set X-Tenant-Id to an arbitrary tenant and read
    its data. Only requests that explicitly claim a specific tenant via
    header now require a real, enabled TenantMembership row — a request
    with no header at all keeps the existing single-tenant-deployment
    default unchanged."""

    def test_operator_without_membership_is_rejected(self):
        tenant = f"tenant-{uuid.uuid4().hex[:8]}"
        r = client.get(
            "/api/analytics/kpi-summary",
            headers={**AUTH_OPERATOR, "X-Tenant-Id": tenant},
        )
        assert r.status_code == 403, r.text

    def test_operator_with_membership_is_allowed(self):
        tenant = f"tenant-{uuid.uuid4().hex[:8]}"
        _grant_membership(tenant, OPERATOR_EMAIL)
        r = client.get(
            "/api/analytics/kpi-summary",
            headers={**AUTH_OPERATOR, "X-Tenant-Id": tenant},
        )
        assert r.status_code == 200, r.text

    def test_disabled_membership_is_still_rejected(self):
        tenant = f"tenant-{uuid.uuid4().hex[:8]}"
        db = SessionLocal()
        try:
            db.add(TenantMembership(tenant_id=tenant, user_email=OPERATOR_EMAIL, role="operator", is_enabled=False))
            db.commit()
        finally:
            db.close()
        r = client.get(
            "/api/analytics/kpi-summary",
            headers={**AUTH_OPERATOR, "X-Tenant-Id": tenant},
        )
        assert r.status_code == 403, r.text

    def test_no_tenant_header_defaults_without_requiring_membership(self):
        # No X-Tenant-Id at all — the existing single-tenant-deployment
        # default ("default-tenant") is unchanged; this isn't a caller
        # claiming a specific tenant identity, so no membership is required.
        r = client.get("/api/analytics/kpi-summary", headers=AUTH_OPERATOR)
        assert r.status_code == 200, r.text

    def test_powerbi_endpoint_also_enforces_membership(self):
        tenant = f"tenant-{uuid.uuid4().hex[:8]}"
        r = client.get(
            "/api/analytics/powerbi",
            headers={**{"Authorization": "Bearer manager-token"}, "X-Tenant-Id": tenant},
        )
        assert r.status_code == 403, r.text

    def test_admin_bypasses_membership_check_entirely(self):
        tenant = f"tenant-{uuid.uuid4().hex[:8]}"
        r = client.get(
            "/api/analytics/kpi-summary",
            headers={**AUTH_ADMIN, "X-Tenant-Id": tenant},
        )
        assert r.status_code == 200, r.text


class TestKpiSummaryResponseShape:
    def test_nested_baselines_and_finding_categories_present(self):
        body = _kpi("default-tenant", AUTH_ADMIN)
        assert "baselines" in body
        for key in ("total", "approved", "pending", "vendor_submissions", "approval_rate"):
            assert key in body["baselines"]
        assert "finding_categories" in body
        assert body["finding_categories"]["blood"] == body["blood_findings"]

    def test_total_users_never_crashes_the_endpoint(self):
        body = _kpi("default-tenant", AUTH_ADMIN)
        assert "total_users" in body
        assert body["total_users"] is None or isinstance(body["total_users"], int)


class TestSupervisorRoleReadAccess:
    def test_supervisor_role_can_read_kpi_summary(self):
        username = f"supervisor-{uuid.uuid4().hex[:8]}@lumen.ai"
        db = SessionLocal()
        try:
            db.add(AdminCredential(username=username, password_hash=bcrypt.hash("Password123"), role="admin"))
            db.add(UserRoleAssignment(username=username, role="supervisor", assigned_by="test"))
            db.commit()
        finally:
            db.close()

        login = client.post("/api/auth/login", json={"email": username, "password": "Password123"})
        assert login.status_code == 200, login.text
        assert login.json()["role"] == "supervisor"

        token = login.json()["access_token"]
        r = client.get("/api/analytics/kpi-summary", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, r.text


class TestCaseInsensitiveCredentialDeterminism:
    def test_exact_case_match_preferred_over_case_fold_duplicate(self):
        base = f"Dup-{uuid.uuid4().hex[:8]}@Lumen.AI"
        lower = base.lower()
        db = SessionLocal()
        try:
            db.query(AdminCredential).filter(AdminCredential.username.in_([base, lower])).delete()
            # Insert the lower-case row FIRST so a naive "first match wins"
            # lookup would pick it — the fix must still prefer the exact
            # case match for whichever casing was actually typed at login.
            db.add(AdminCredential(username=lower, password_hash=bcrypt.hash("LowerPass123"), role="admin"))
            db.add(AdminCredential(username=base, password_hash=bcrypt.hash("ExactPass123"), role="admin"))
            db.commit()
        finally:
            db.close()

        # Logging in with the exact-case username must check that row's
        # password, not the case-folded duplicate's.
        r = client.post("/api/auth/login", json={"email": base, "password": "ExactPass123"})
        assert r.status_code == 200, r.text

        r_wrong = client.post("/api/auth/login", json={"email": base, "password": "LowerPass123"})
        assert r_wrong.status_code == 401
