import os


def get_allowed_origins() -> list[str]:
    raw = os.getenv("ALLOWED_ORIGINS", "").strip()

    if raw:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    from app.core.environment import is_production

    app_env = os.getenv("APP_ENV", os.getenv("ENV", "development")).strip().lower()

    # PA-1: canonical production determination (APP_ENV or ENVIRONMENT), plus the
    # legacy ENV fallback this function always honoured.
    if is_production() or app_env in {"production", "prod"}:
        return ["https://lumen-ai-1.onrender.com"]

    return [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://localhost:5177",
        "http://localhost:5178",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://127.0.0.1:5176",
        "http://127.0.0.1:5177",
        "http://127.0.0.1:5178",
    ]
