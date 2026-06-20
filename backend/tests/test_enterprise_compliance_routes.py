import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")


def _collect_all_paths(router_or_app) -> set:
    paths = set()
    obj = getattr(router_or_app, "router", router_or_app)
    for route in getattr(obj, "routes", []):
        p = getattr(route, "path", None)
        if p:
            paths.add(p)
        orig = getattr(route, "original_router", None)
        if orig:
            paths |= _collect_all_paths(orig)
    return paths


def test_enterprise_app_imports():
    from app.main import app

    assert app is not None


def test_critical_compliance_routes_registered():
    from app.main import app

    paths = _collect_all_paths(app)

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
