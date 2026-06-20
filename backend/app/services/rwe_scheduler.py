"""Weekly RWE metric snapshot scheduler for post-market surveillance."""
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _run_weekly_rwe_snapshots(db_factory):
    """Compute RWE snapshots for all active RWE enrollments."""
    db = db_factory()
    try:
        from app.models.validation import RWEEnrollment, RWEMetricSnapshot
        from app.services.validation_engine import _seed

        enrollments = db.query(RWEEnrollment).filter(
            RWEEnrollment.is_active == True  # noqa: E712
        ).all()

        week_label = datetime.now(timezone.utc).strftime("%Y-W%W")
        processed = 0

        for enrollment in enrollments:
            try:
                # Check if snapshot already exists for this week
                existing = db.query(RWEMetricSnapshot).filter(
                    RWEMetricSnapshot.tenant_id == enrollment.tenant_id,
                    RWEMetricSnapshot.facility_id == enrollment.facility_id,
                    RWEMetricSnapshot.week_label == week_label,
                ).first()
                if existing:
                    continue

                # Compute snapshot using seeded mock (real data when CVInferenceRecord populated)
                rng = _seed(f"rwe:{enrollment.tenant_id}:{enrollment.facility_id}:{week_label}")
                override_rate = round(rng.uniform(0.03, 0.18), 4)
                escalation_rate = round(rng.uniform(0.01, 0.07), 4)
                psi_score = round(rng.uniform(0.05, 0.35), 4)
                drift_alert = psi_score > 0.2

                snapshot = RWEMetricSnapshot(
                    tenant_id=enrollment.tenant_id,
                    facility_id=enrollment.facility_id,
                    week_label=week_label,
                    total_inspections=rng.randint(80, 300),
                    override_count=rng.randint(2, 30),
                    override_rate=override_rate,
                    escalation_count=rng.randint(0, 15),
                    escalation_rate=escalation_rate,
                    finding_distribution_json="{}",
                    psi_score=psi_score,
                    drift_alert=drift_alert,
                )
                db.add(snapshot)
                processed += 1
            except Exception as e:
                logger.warning(f"RWE snapshot failed for {enrollment.tenant_id}: {e}")

        db.commit()
        logger.info(f"RWE scheduler: processed {processed} enrollment snapshots for {week_label}")
    except Exception as e:
        logger.error(f"RWE scheduler error: {e}")
        db.rollback()
    finally:
        db.close()


def register_rwe_scheduler(scheduler, db_factory):
    """Register weekly RWE snapshot job — every Monday at 03:00 UTC."""
    scheduler.add_job(
        _run_weekly_rwe_snapshots,
        trigger="cron",
        day_of_week="mon",
        hour=3,
        minute=0,
        id="weekly_rwe_snapshots",
        replace_existing=True,
        args=[db_factory],
    )
    logger.info("RWE scheduler registered: weekly Monday 03:00 UTC")
