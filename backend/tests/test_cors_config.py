from app.core.cors import get_allowed_origins


def test_production_cors_defaults_to_public_frontend(monkeypatch):
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    monkeypatch.setenv("APP_ENV", "production")

    assert get_allowed_origins() == ["https://lumen-ai-1.onrender.com"]


def test_allowed_origins_env_is_parsed(monkeypatch):
    monkeypatch.setenv(
        "ALLOWED_ORIGINS",
        "https://lumen-ai-1.onrender.com,http://localhost:5173",
    )

    assert get_allowed_origins() == [
        "https://lumen-ai-1.onrender.com",
        "http://localhost:5173",
    ]


def test_development_cors_includes_localhost(monkeypatch):
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    monkeypatch.setenv("APP_ENV", "development")

    origins = get_allowed_origins()

    assert "http://localhost:5173" in origins
    assert "http://localhost:5178" in origins
    assert "*" not in origins
