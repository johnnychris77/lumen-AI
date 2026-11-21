"""Canonical production-environment determination (P472-03 PA-1 remediation).

Before this module, every privileged-access gate read its own environment
variable (RB-T38…RB-T40):

* ``app.deps`` dev-token map: ``APP_ENV`` only;
* ``app.main`` startup guards: ``APP_ENV`` or ``ENVIRONMENT``;
* ``enterprise_auth`` JWT-shape check: ``ENVIRONMENT == "production"`` exactly;
* ``/api/demo/*``: ``DEMO_MODE`` only, with no production check.

Every gate now asks :func:`is_production`. It reads **both** signal variables,
case-insensitively and stripped, and is production when **either** names a
production value. It never weakens a gate: any production signal is production.

Fail-closed startup (:func:`production_configuration_errors`, enforced by
``app.main``): the process refuses to start when

* the two signals **conflict** (one production, the other set to a
  non-production value) — the deployment intent is ambiguous;
* a production process enables development authentication: ``AUTH_MODE`` is
  unset or anything other than ``oidc`` (``AUTH_MODE=dev`` is refused; the old
  ``ALLOW_DEV_AUTH_IN_PROD`` acknowledgment is **no longer honoured**), or
  ``ENABLE_DEV_AUTH`` is true;
* a production process enables the unauthenticated demo routes (``DEMO_MODE``);
* ``SECRET_KEY`` is unset or a known-weak value (unchanged rule).

The runtime gates also call :func:`is_production` themselves, so a module used
without ``app.main`` (a worker, a script, a test harness) still fails closed.

This module grants nothing. It only removes development and demo credentials
from production; it creates no role, membership or administrator.
"""
from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

PRODUCTION_VALUES = frozenset({"production", "prod"})
SIGNAL_VARIABLES = ("APP_ENV", "ENVIRONMENT")
PRODUCTION_AUTH_MODES = frozenset({"oidc"})
_FALSE_VALUES = frozenset({"", "0", "false", "no", "off"})


def _normalise(value: str | None) -> str | None:
    value = (value or "").strip().lower()
    return value or None


def _flag_enabled(value: str | None) -> bool:
    return (value or "").strip().lower() not in _FALSE_VALUES


@dataclass(frozen=True)
class EnvironmentDetermination:
    """The normalised production signals and what they mean."""

    signals: dict[str, str | None]
    is_production: bool
    conflict: str | None

    @property
    def production_signals(self) -> tuple[str, ...]:
        return tuple(n for n, v in self.signals.items() if v in PRODUCTION_VALUES)


def determine_environment(environ: Mapping[str, str] | None = None) -> EnvironmentDetermination:
    """Read ``APP_ENV`` and ``ENVIRONMENT`` once, the same way for every caller."""
    env = os.environ if environ is None else environ
    signals = {name: _normalise(env.get(name)) for name in SIGNAL_VARIABLES}
    production = [n for n, v in signals.items() if v in PRODUCTION_VALUES]
    non_production = [n for n, v in signals.items() if v is not None and v not in PRODUCTION_VALUES]
    conflict = None
    if production and non_production:
        conflict = (
            "conflicting environment signals: "
            + ", ".join(f"{n}={signals[n]}" for n in SIGNAL_VARIABLES if signals[n] is not None)
            + ". Set APP_ENV and ENVIRONMENT to the same value (or leave one unset)."
        )
    # A conflict counts as production so that every runtime gate fails closed.
    return EnvironmentDetermination(signals=signals, is_production=bool(production), conflict=conflict)


def is_production(environ: Mapping[str, str] | None = None) -> bool:
    """True when either production signal names production. The single answer for every gate."""
    return determine_environment(environ).is_production


def production_configuration_errors(environ: Mapping[str, str] | None = None) -> list[str]:
    """Every reason a production process must refuse to start. Empty outside production."""
    env = os.environ if environ is None else environ
    determination = determine_environment(env)
    errors: list[str] = []
    if determination.conflict:
        errors.append(determination.conflict)
    if not determination.is_production:
        return errors

    from app.config import KNOWN_WEAK_SECRET_KEYS

    if env.get("SECRET_KEY", "dev-secret-change-in-production") in KNOWN_WEAK_SECRET_KEYS:
        errors.append(
            "SECRET_KEY is unset or a known-weak default value in a production environment. "
            "Set a strong, non-default SECRET_KEY before starting."
        )

    auth_mode = _normalise(env.get("AUTH_MODE"))
    if auth_mode is None:
        errors.append(
            "AUTH_MODE is not set in a production environment. Set AUTH_MODE=oidc with "
            "OIDC_ISSUER_URL and OIDC_AUDIENCE."
        )
    elif auth_mode not in PRODUCTION_AUTH_MODES:
        errors.append(
            f"AUTH_MODE={auth_mode} is not permitted in a production environment: development "
            "authentication trusts client-supplied identity headers. Use AUTH_MODE=oidc. "
            "ALLOW_DEV_AUTH_IN_PROD is no longer honoured (PA-1 remediation)."
        )

    if _flag_enabled(env.get("ENABLE_DEV_AUTH")):
        errors.append(
            "ENABLE_DEV_AUTH is enabled in a production environment; development tokens must "
            "never authenticate in production. Set ENABLE_DEV_AUTH=false."
        )

    if _flag_enabled(env.get("DEMO_MODE")):
        errors.append(
            "DEMO_MODE is enabled in a production environment; the demo routes (including the "
            "data-deleting /api/demo/reset) accept public literal tokens. Unset DEMO_MODE."
        )
    return errors


def startup_refusal_message(environ: Mapping[str, str] | None = None) -> str | None:
    """The ``sys.exit`` message for ``app.main``, or None when the configuration may start."""
    errors = production_configuration_errors(environ)
    if not errors:
        return None
    return "FATAL: refusing to start (production configuration check): " + " | ".join(errors)
