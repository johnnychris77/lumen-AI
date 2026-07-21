from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


# SEC-H-01/02 — known-weak HS256 signing secrets that must never be used in a
# production deployment. Both historical hardcoded fallbacks are listed so a
# deploy that explicitly set either (or left SECRET_KEY unset) is caught, not
# just the one string the earlier startup guard checked. Empty string covers an
# explicitly-blank SECRET_KEY.
KNOWN_WEAK_SECRET_KEYS = frozenset({
    "",
    "dev-secret",
    "dev-secret-change-in-production",
})


@dataclass(frozen=True)
class Settings:
    app_env: str
    api_prefix: str
    public_base_url: str

    database_url: str

    secret_key: str

    dev_auth_token: str
    enable_dev_auth: bool

    portfolio_briefing_scheduler_seconds: int
    executive_kpi_scheduler_hours: int

    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    smtp_from: str
    smtp_use_tls: bool

    default_webhook_url: str

    portfolio_briefing_artifact_root: str
    governance_packet_artifact_root: str
    reports_root: str

    enable_enterprise_audit: bool
    enable_enterprise_rbac: bool

    # v1.2 — Guided Capture coverage gate. When True, an inspection with
    # incomplete/insufficient coverage cannot reach a final AI decision
    # without a recorded supervisor override (see app/services/guided_capture.py).
    # Default False: non-blocking, matching the v1.1 "advisory, not a gate" default.
    require_full_coverage_before_final_decision: bool

    allowed_origins: list[str]

    # Project Vision Sprint 2, Section 15 — "placeholder inference may exist
    # only in explicit test/demo mode and must never run silently in
    # production." Defaults to False everywhere, including real production
    # deployments (APP_ENV=production is already set there today), so
    # enabling this is a deliberate, separate decision from is_production —
    # not an automatic consequence of it. When True,
    # baseline_comparison_scoring_service._build_model_result() reports the
    # honest "unavailable" state instead of a deterministic-placeholder
    # probability for any category no real promoted model backs, rather
    # than presenting a fabricated score as if it were evaluated.
    ai_strict_no_placeholder: bool

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}

    def validate(self) -> list[str]:
        issues: list[str] = []

        if not self.database_url:
            issues.append("DATABASE_URL is required.")

        # SEC-H-01/02 — the HS256 signing secret must be a strong, non-default
        # value in production. A weak/default secret lets anyone mint valid
        # tokens, so this is fail-closed at startup (see app/main.py).
        if self.is_production and self.secret_key in KNOWN_WEAK_SECRET_KEYS:
            issues.append(
                "SECRET_KEY must be set to a strong, non-default value in production."
            )

        if self.is_production and self.enable_dev_auth:
            issues.append("ENABLE_DEV_AUTH should be false in production.")

        if self.is_production and self.dev_auth_token == "dev-token":
            issues.append("DEV_AUTH_TOKEN must not remain dev-token in production.")

        if self.public_base_url.startswith("http://127.0.0.1") and self.is_production:
            issues.append("PUBLIC_BASE_URL should not point to localhost in production.")

        if self.smtp_password and not self.smtp_host:
            issues.append("SMTP_PASSWORD is set but SMTP_HOST is missing.")

        return issues


def get_settings() -> Settings:
    allowed_origins = [
        item.strip()
        for item in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173,http://localhost:9092,http://127.0.0.1:9092,http://localhost:18011,http://127.0.0.1:18011,https://lumen-ai-53u4.onrender.com,https://lumen-ai-1.onrender.com").split(",")
        if item.strip()
    ]

    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        api_prefix=os.getenv("API_PREFIX", "/api"),
        public_base_url=os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:18011").rstrip("/"),
        database_url=os.getenv("DATABASE_URL", ""),
        secret_key=os.getenv("SECRET_KEY", "dev-secret-change-in-production"),
        dev_auth_token=os.getenv("DEV_AUTH_TOKEN", "dev-token"),
        enable_dev_auth=_bool_env("ENABLE_DEV_AUTH", False),
        portfolio_briefing_scheduler_seconds=_int_env("PORTFOLIO_BRIEFING_SCHEDULER_SECONDS", 60),
        executive_kpi_scheduler_hours=_int_env("EXECUTIVE_KPI_SCHEDULER_HOURS", 24),
        smtp_host=os.getenv("SMTP_HOST", ""),
        smtp_port=_int_env("SMTP_PORT", 587),
        smtp_user=os.getenv("SMTP_USER", ""),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        smtp_from=os.getenv("SMTP_FROM", ""),
        smtp_use_tls=_bool_env("SMTP_USE_TLS", True),
        default_webhook_url=os.getenv("DEFAULT_WEBHOOK_URL", ""),
        portfolio_briefing_artifact_root=os.getenv("PORTFOLIO_BRIEFING_ARTIFACT_ROOT", "generated_portfolio_briefings"),
        governance_packet_artifact_root=os.getenv("GOVERNANCE_PACKET_ARTIFACT_ROOT", "generated_governance_packets"),
        reports_root=os.getenv("REPORTS_ROOT", "reports"),
        enable_enterprise_audit=_bool_env("ENABLE_ENTERPRISE_AUDIT", True),
        enable_enterprise_rbac=_bool_env("ENABLE_ENTERPRISE_RBAC", True),
        require_full_coverage_before_final_decision=_bool_env("REQUIRE_FULL_COVERAGE_BEFORE_FINAL_DECISION", False),
        allowed_origins=allowed_origins,
        ai_strict_no_placeholder=_bool_env("AI_STRICT_NO_PLACEHOLDER", False),
    )


def ensure_runtime_directories() -> None:
    settings = get_settings()

    for path in [
        settings.portfolio_briefing_artifact_root,
        settings.governance_packet_artifact_root,
        settings.reports_root,
    ]:
        Path(path).mkdir(parents=True, exist_ok=True)
