"""RES-01 — lease-based leader election for the background schedulers.

Only the current lease holder runs the scheduled jobs. Leadership is a
time-bounded lease renewed by the holder on a heartbeat; if the holder dies and
stops renewing, the lease expires and a standby replica claims it — automatic
failover within `ttl_seconds`.

The core primitive is a single atomic conditional UPDATE:

    UPDATE scheduler_leader
       SET holder = :me, expires_at = :new_expiry
     WHERE lock_name = :name
       AND (expires_at < :now OR holder = :me)

A single UPDATE statement is atomic on both PostgreSQL and SQLite, so at most
one replica can transition the row from "expired/free" to "held by me" for a
given `now`. Renewal by the current holder is the `holder = :me` branch.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

logger = logging.getLogger(__name__)

DEFAULT_LOCK = "global-scheduler"
DEFAULT_TTL_SECONDS = 60


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def acquire_or_renew(
    session_factory,
    holder: str,
    lock_name: str = DEFAULT_LOCK,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> bool:
    """Try to acquire the lock (if free/expired) or renew it (if already ours).

    Returns True iff `holder` owns the lock after this call. Best-effort and
    non-fatal: a DB error returns False (this replica simply does not lead).
    """
    now = _utcnow()
    new_expiry = now + timedelta(seconds=ttl_seconds)
    session = session_factory()
    try:
        # Fast path: claim/renew via an atomic conditional UPDATE.
        result = session.execute(
            text(
                "UPDATE scheduler_leader "
                "SET holder = :me, expires_at = :new_expiry "
                "WHERE lock_name = :name "
                "AND (expires_at < :now OR holder = :me)"
            ),
            {"me": holder, "new_expiry": new_expiry, "name": lock_name, "now": now},
        )
        if result.rowcount and result.rowcount > 0:
            session.commit()
            return True

        # No row updated: either the row does not exist yet, or another holder
        # owns an unexpired lease. Try a one-time insert to bootstrap the row.
        session.rollback()
        try:
            session.execute(
                text(
                    "INSERT INTO scheduler_leader (lock_name, holder, expires_at) "
                    "VALUES (:name, :me, :new_expiry)"
                ),
                {"name": lock_name, "me": holder, "new_expiry": new_expiry},
            )
            session.commit()
            return True
        except Exception:
            # Row already exists and is held by a live leader — we are a standby.
            session.rollback()
            return False
    except Exception as exc:  # pragma: no cover - DB failure => not leader
        session.rollback()
        logger.warning("Leader election acquire/renew failed for %s: %s", lock_name, exc)
        return False
    finally:
        session.close()


def is_leader(session_factory, holder: str, lock_name: str = DEFAULT_LOCK) -> bool:
    """True iff `holder` currently owns an unexpired lease for `lock_name`."""
    # Read through the ORM so the DateTime column type coerces `expires_at`
    # back into a real datetime (a raw text() SELECT returns a bare string on
    # SQLite, which would misfire the expiry comparison).
    from app.models.scheduler_leader import SchedulerLeader

    session = session_factory()
    try:
        row = session.get(SchedulerLeader, lock_name)
        if row is None or row.holder != holder or row.expires_at is None:
            return False
        expires_at = row.expires_at
        # SQLite returns a naive datetime; treat it as UTC for comparison.
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return expires_at >= _utcnow()
    except Exception as exc:  # pragma: no cover
        logger.warning("Leader check failed for %s: %s", lock_name, exc)
        return False
    finally:
        session.close()


def release(session_factory, holder: str, lock_name: str = DEFAULT_LOCK) -> None:
    """Relinquish leadership if we hold it, so a standby can take over promptly."""
    session = session_factory()
    try:
        session.execute(
            text(
                "UPDATE scheduler_leader SET expires_at = :past "
                "WHERE lock_name = :name AND holder = :me"
            ),
            {"past": _utcnow() - timedelta(seconds=1), "name": lock_name, "me": holder},
        )
        session.commit()
    except Exception as exc:  # pragma: no cover
        session.rollback()
        logger.warning("Leader release failed for %s: %s", lock_name, exc)
    finally:
        session.close()
