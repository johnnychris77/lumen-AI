"""Standalone rate limiter module — import from here to avoid circular imports."""
import os

_enabled = os.getenv("RATELIMIT_ENABLED", "1") != "0"

try:
    if _enabled:
        from slowapi import Limiter
        from slowapi.util import get_remote_address

        limiter = Limiter(key_func=get_remote_address)
    else:
        limiter = None
except Exception:
    limiter = None


def _rate_limit(rate: str):
    """Apply rate limit if limiter available, else no-op decorator."""
    if limiter is not None:
        return limiter.limit(rate)
    return lambda f: f
