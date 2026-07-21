"""SEC-H-01/02 — the HS256 signing secret must be strong in production.

Covers three gaps closed in this change:
  * `Settings.validate()` now flags a weak/default SECRET_KEY in production
    (previously it omitted SECRET_KEY entirely).
  * The known-weak set includes BOTH historical hardcoded fallbacks
    ("dev-secret" and "dev-secret-change-in-production") plus unset/empty, so a
    deploy that set either is caught — not just the one string.
  * `core/config.py` no longer defaults to the divergent weak "dev-secret".
"""
import importlib
import os

from app.config import KNOWN_WEAK_SECRET_KEYS, get_settings


def _settings_with(env: dict):
    old = {k: os.environ.get(k) for k in env}
    try:
        for k, v in env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        return get_settings()
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_known_weak_set_covers_both_historical_defaults():
    assert "dev-secret" in KNOWN_WEAK_SECRET_KEYS
    assert "dev-secret-change-in-production" in KNOWN_WEAK_SECRET_KEYS
    assert "" in KNOWN_WEAK_SECRET_KEYS


def test_validate_flags_weak_secret_in_production():
    for weak in ("dev-secret", "dev-secret-change-in-production", ""):
        s = _settings_with({"APP_ENV": "production", "SECRET_KEY": weak,
                            "DATABASE_URL": "sqlite:///./x.db"})
        issues = s.validate()
        assert any("SECRET_KEY" in i for i in issues), f"weak={weak!r} not flagged: {issues}"


def test_validate_accepts_strong_secret_in_production():
    s = _settings_with({"APP_ENV": "production",
                        "SECRET_KEY": "a-strong-random-value-9f3b7c2e1d",
                        "DATABASE_URL": "sqlite:///./x.db"})
    assert not any("SECRET_KEY" in i for i in s.validate())


def test_validate_silent_in_development():
    # A weak/unset secret is fine in dev — must NOT be flagged.
    s = _settings_with({"APP_ENV": "development", "SECRET_KEY": None,
                        "DATABASE_URL": "sqlite:///./x.db"})
    assert not any("SECRET_KEY" in i for i in s.validate())


def test_core_config_no_longer_defaults_to_weak_dev_secret():
    old = os.environ.pop("SECRET_KEY", None)
    try:
        import app.core.config as core_config
        importlib.reload(core_config)
        # The removed divergent default must be gone; the fallback is the single
        # canonical dev value the production guard rejects.
        assert core_config.settings.SECRET_KEY != "dev-secret"
        assert core_config.settings.SECRET_KEY == "dev-secret-change-in-production"
    finally:
        if old is not None:
            os.environ["SECRET_KEY"] = old
        import app.core.config as core_config
        importlib.reload(core_config)
