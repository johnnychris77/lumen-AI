import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")


def test_enterprise_app_imports():
    from app.main import app

    assert app is not None


def test_critical_compliance_routes_registered():
    from app.main import app

    paths = {route.path for route in app.routes}

    expected_paths = {
        "/api/enterprise/vendor-baseline-subscription/baselines",
        "/api/enterprise/vendor-baseline-subscription/baselines/{baseline_id}/approve",
        "/api/enterprise/vendor-baseline-subscription/baselines/{baseline_id}/audit",
        "/api/enterprise/intake/{finding_id}/governance-packet.pdf",
        "/api/enterprise/intake/{finding_id}/governance-export-history",
        "/api/enterprise/intake/{finding_id}/governance-packet/verify-hash",
    }

    missing = expected_paths - paths

    assert not missing, f"Missing critical compliance routes: {sorted(missing)}"
