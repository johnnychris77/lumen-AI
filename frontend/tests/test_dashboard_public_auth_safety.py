from pathlib import Path


def test_public_dashboard_does_not_contain_dev_auth_headers():
    dashboard = Path("public/dashboard/index.html").read_text(encoding="utf-8").lower()

    forbidden_terms = [
        "dev-token",
        "authorization:",
        "x-lumenai-role",
        "x-lumenai-actor",
        "enterprise_admin",
        "/api/enterprise/audit",
        "/api/capa",
        "/api/analytics/vendors",
        "/api/enterprise/audit/evidence-bundle",
    ]

    for term in forbidden_terms:
        assert term not in dashboard


def test_public_dashboard_uses_public_module_status_endpoint():
    dashboard = Path("public/dashboard/index.html").read_text(encoding="utf-8")

    assert "/api/public/module-status/all" in dashboard
