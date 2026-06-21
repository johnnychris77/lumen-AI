"""
Safe demo seed data for local development and staging validation.

Run with:
  DATABASE_URL=sqlite:///./lumenai.db PYTHONPATH=. python -m app.seed_demo

Idempotent: checks for existing records before inserting.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone

from app.db.base import Base
from app.db.session import SessionLocal, engine


def _now() -> datetime:
    return datetime.now(timezone.utc)


def run_seed() -> None:
    Base.metadata.create_all(bind=engine)

    from app.models.enterprise_quality import (
        EnterpriseDepartment,
        EnterpriseFacility,
        EnterpriseFinding,
        EnterpriseInstrument,
        EnterpriseVendor,
        EnterpriseVendorBaselineSubscription,
    )

    db = SessionLocal()
    try:
        # ── Facility ──────────────────────────────────────────────────────────
        facility = db.query(EnterpriseFacility).filter_by(name="St. Mary's Hospital").first()
        if not facility:
            facility = EnterpriseFacility(
                tenant_id="demo-tenant",
                name="St. Mary's Hospital",
                facility_type="hospital",
                region="Mid-Atlantic",
                status="active",
                created_at=_now(),
            )
            db.add(facility)
            db.flush()
            print(f"  + Facility: {facility.name} (id={facility.id})")
        else:
            print(f"  = Facility already exists (id={facility.id})")

        # ── Department ────────────────────────────────────────────────────────
        department = db.query(EnterpriseDepartment).filter_by(
            facility_id=facility.id, name="Sterile Processing"
        ).first()
        if not department:
            department = EnterpriseDepartment(
                tenant_id="demo-tenant",
                facility_id=facility.id,
                name="Sterile Processing",
                department_type="spd",
                status="active",
                created_at=_now(),
            )
            db.add(department)
            db.flush()
            print(f"  + Department: {department.name} (id={department.id})")
        else:
            print(f"  = Department already exists (id={department.id})")

        # ── Vendor ────────────────────────────────────────────────────────────
        vendor = db.query(EnterpriseVendor).filter_by(name="Stryker Medical Devices").first()
        if not vendor:
            vendor = EnterpriseVendor(
                tenant_id="demo-tenant",
                name="Stryker Medical Devices",
                vendor_type="medical_device",
                contact_name="Jane Vendor",
                contact_email="jane@stryker-demo.example.com",
                risk_tier="tier_1",
                status="active",
                created_at=_now(),
            )
            db.add(vendor)
            db.flush()
            print(f"  + Vendor: {vendor.name} (id={vendor.id})")
        else:
            print(f"  = Vendor already exists (id={vendor.id})")

        # ── Instrument ────────────────────────────────────────────────────────
        instrument = db.query(EnterpriseInstrument).filter_by(
            name="Frazier Suction Tube 8Fr"
        ).first()
        if not instrument:
            instrument = EnterpriseInstrument(
                tenant_id="demo-tenant",
                vendor_id=vendor.id,
                name="Frazier Suction Tube 8Fr",
                instrument_type="lumened_instrument",
                category="lumened instrument",
                model_number="FRAZ-8FR-001",
                serial_number="SN-DEMO-0001",
                risk_class="high",
                ifu_reference="IFU-STRYKER-FRAZ-8FR-v2.1",
                status="active",
                created_at=_now(),
            )
            db.add(instrument)
            db.flush()
            print(f"  + Instrument: {instrument.name} (id={instrument.id})")
        else:
            print(f"  = Instrument already exists (id={instrument.id})")

        # ── Finding ───────────────────────────────────────────────────────────
        finding = db.query(EnterpriseFinding).filter_by(id=1).first()
        if not finding:
            finding = EnterpriseFinding(
                id=1,
                tenant_id="demo-tenant",
                instrument_id=instrument.id,
                vendor_id=vendor.id,
                finding_category="bioburden / retained debris",
                finding_description=(
                    "Suspected retained debris identified during borescope inspection "
                    "of Frazier suction tube lumen. Baseline comparison flagged deviation."
                ),
                severity="critical",
                confidence_score=0.91,
                human_confirmed=False,
                created_at=_now(),
            )
            db.add(finding)
            db.flush()
            print(f"  + Finding: id={finding.id}")
        else:
            print("  = Finding id=1 already exists")

        # ── Vendor Baseline — pending review ──────────────────────────────────
        pending_baseline = db.query(EnterpriseVendorBaselineSubscription).filter_by(
            vendor_name="Stryker Medical Devices",
            instrument_name="Frazier Suction Tube 8Fr",
            approval_status="pending_hospital_review",
        ).first()
        if not pending_baseline:
            pending_baseline = EnterpriseVendorBaselineSubscription(
                vendor_name="Stryker Medical Devices",
                instrument_name="Frazier Suction Tube 8Fr",
                instrument_category="lumened instrument",
                catalog_number="FRAZ-8FR-001",
                model_number="STR-FST-8FR",
                barcode_value="STRYKER-FRAZ-8FR-001",
                qr_code_value="QR-STR-FRAZ-8FR-001",
                key_dot_value="",
                tray_name="General Neuro Tray A",
                baseline_image_url="https://demo.lumenai.example.com/baselines/stryker-fraz-8fr-baseline.jpg",
                acceptable_condition_notes=(
                    "Lumen clear, no debris visible under borescope. "
                    "Port markings intact. Suction port free of biofilm."
                ),
                unacceptable_condition_examples=(
                    "Debris visible in lumen, discoloration at distal end, "
                    "compromised port seals, visible corrosion."
                ),
                ifu_reference="IFU-STRYKER-FRAZ-8FR-v2.1",
                subscription_tier="vendor_enterprise",
                baseline_source="vendor",
                baseline_status="vendor_submitted",
                approval_status="pending_hospital_review",
                baseline_version="v1.0",
                created_at=_now(),
                updated_at=_now(),
            )
            db.add(pending_baseline)
            db.flush()
            print(f"  + Vendor Baseline (pending): id={pending_baseline.id}")
        else:
            print(f"  = Pending vendor baseline already exists (id={pending_baseline.id})")

        # ── Vendor Baseline — approved ─────────────────────────────────────────
        approved_baseline = db.query(EnterpriseVendorBaselineSubscription).filter_by(
            vendor_name="Stryker Medical Devices",
            instrument_name="Kerrison Rongeur 3mm",
            approval_status="approved",
        ).first()
        if not approved_baseline:
            approved_baseline = EnterpriseVendorBaselineSubscription(
                vendor_name="Stryker Medical Devices",
                instrument_name="Kerrison Rongeur 3mm",
                instrument_category="non-lumened instrument",
                catalog_number="KR-3MM-STR",
                model_number="STR-KR-3MM",
                barcode_value="STRYKER-KR-3MM-001",
                qr_code_value="QR-STR-KR-3MM",
                key_dot_value="KD-KR-3MM",
                tray_name="Spine Tray B",
                baseline_image_url="https://demo.lumenai.example.com/baselines/stryker-kr-3mm-baseline.jpg",
                acceptable_condition_notes=(
                    "Jaws close cleanly, no bending or chipping. "
                    "Hinge mechanism smooth. No corrosion on cutting edges."
                ),
                unacceptable_condition_examples=(
                    "Chipped or bent jaws, stuck hinge, rust on cutting surfaces, "
                    "missing key-dot identification marker."
                ),
                ifu_reference="IFU-STRYKER-KR-3MM-v1.4",
                subscription_tier="vendor_enterprise",
                baseline_source="vendor",
                baseline_status="approved",
                approval_status="approved",
                approved_by="hospital-admin@bonsecours-demo.example.com",
                approval_notes="Baseline meets Bon Secours sterile processing standards. Approved for use.",
                baseline_version="v1.0",
                created_at=_now(),
                updated_at=_now(),
            )
            db.add(approved_baseline)
            db.flush()
            print(f"  + Vendor Baseline (approved): id={approved_baseline.id}")
        else:
            print(f"  = Approved vendor baseline already exists (id={approved_baseline.id})")

        # ── Pilot KPI findings (one per category) ────────────────────────────
        pilot_categories = [
            ("blood / retained blood residue", "Blood residue detected in lumen channel during borescope inspection. Staining consistent with retained hemoglobin.", "critical"),
            ("bone / bone fragment", "Bone fragment identified at distal port of suction instrument. Detected via AI baseline comparison.", "high"),
            ("tissue / retained tissue", "Retained soft tissue fragment visible at instrument tip. Baseline deviation flagged for IP review.", "high"),
            ("debris / retained debris", "Non-biological debris identified in lumen. Source unknown; quarantine recommended.", "medium"),
            ("corrosion / surface rust", "Surface corrosion noted on instrument shaft. Structural integrity uncompromised but flagged for replacement review.", "medium"),
            ("crack / hairline fracture", "Hairline crack detected near instrument hub during visual inspection. Risk of metal shedding.", "critical"),
            ("insulation damage", "Insulation degradation identified on electrosurgical instrument. Electrical safety risk flagged.", "critical"),
        ]
        for cat, desc, sev in pilot_categories:
            existing = db.query(EnterpriseFinding).filter_by(
                finding_category=cat, tenant_id="demo-tenant"
            ).first()
            if not existing:
                pf = EnterpriseFinding(
                    tenant_id="demo-tenant",
                    instrument_id=instrument.id,
                    vendor_id=vendor.id,
                    finding_category=cat,
                    finding_description=desc,
                    severity=sev,
                    confidence_score=0.88,
                    human_confirmed=False,
                    created_at=_now(),
                )
                db.add(pf)
                db.flush()
                print(f"  + Pilot finding: {cat[:40]} (id={pf.id})")
            else:
                print(f"  = Pilot finding already exists: {cat[:40]}")

        db.commit()
        print("\nDemo seed complete.")
        print(f"  Facility id:            {facility.id}")
        print(f"  Department id:          {department.id}")
        print(f"  Vendor id:              {vendor.id}")
        print(f"  Instrument id:          {instrument.id}")
        print(f"  Finding id:             {finding.id}")
        print(f"  Pending baseline id:    {pending_baseline.id}")
        print(f"  Approved baseline id:   {approved_baseline.id}")

    except Exception as exc:
        db.rollback()
        print(f"Seed failed: {exc}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Running LumenAI demo seed...")
    run_seed()
