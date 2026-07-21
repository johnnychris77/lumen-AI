"""RES-01 — leader election gives exactly one holder, with failover.

A single-statement conditional UPDATE means only one replica can hold the lease
at a time; a standby can claim it only once the current lease expires.
"""
from datetime import timedelta

import app.db.models  # noqa: F401 — establish full model registry order first
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.models.scheduler_leader import SchedulerLeader
from app.services import scheduler_leader as sl


def _factory(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path/'leader.db'}")
    SchedulerLeader.__table__.create(engine)
    return sessionmaker(bind=engine, autoflush=False), engine


def test_first_replica_acquires_and_can_renew(tmp_path):
    Session, _ = _factory(tmp_path)
    assert sl.acquire_or_renew(Session, "replica-A", ttl_seconds=60) is True
    assert sl.is_leader(Session, "replica-A") is True
    # Renewal by the same holder keeps leadership.
    assert sl.acquire_or_renew(Session, "replica-A", ttl_seconds=60) is True
    assert sl.is_leader(Session, "replica-A") is True


def test_second_replica_is_rejected_while_lease_valid(tmp_path):
    Session, _ = _factory(tmp_path)
    assert sl.acquire_or_renew(Session, "replica-A", ttl_seconds=60) is True
    # Standby cannot steal an unexpired lease → exactly one leader.
    assert sl.acquire_or_renew(Session, "replica-B", ttl_seconds=60) is False
    assert sl.is_leader(Session, "replica-B") is False
    assert sl.is_leader(Session, "replica-A") is True


def test_standby_takes_over_after_lease_expires(tmp_path):
    Session, engine = _factory(tmp_path)
    assert sl.acquire_or_renew(Session, "replica-A", ttl_seconds=60) is True
    # Simulate replica-A dying: force its lease into the past.
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE scheduler_leader SET expires_at = :past WHERE lock_name = :n"),
            {"past": sl._utcnow() - timedelta(seconds=5), "n": sl.DEFAULT_LOCK},
        )
    assert sl.is_leader(Session, "replica-A") is False  # lease lapsed
    # Standby now claims leadership → automatic failover.
    assert sl.acquire_or_renew(Session, "replica-B", ttl_seconds=60) is True
    assert sl.is_leader(Session, "replica-B") is True
    assert sl.is_leader(Session, "replica-A") is False


def test_release_lets_standby_take_over_immediately(tmp_path):
    Session, _ = _factory(tmp_path)
    assert sl.acquire_or_renew(Session, "replica-A", ttl_seconds=60) is True
    sl.release(Session, "replica-A")
    assert sl.is_leader(Session, "replica-A") is False
    # After a graceful release the standby can lead without waiting for TTL.
    assert sl.acquire_or_renew(Session, "replica-B", ttl_seconds=60) is True
    assert sl.is_leader(Session, "replica-B") is True
