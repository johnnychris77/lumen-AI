"""
Pilot Data Seed Script — Phase 7

Seeds the first production-quality pilot dataset:
  - 10 lumened instrument digital identity records
  - 25 baseline library entries (mix of pending/approved)
  - 50 inspection records with realistic finding distribution

Usage:
    cd backend
    PYTHONPATH=. DATABASE_URL=sqlite:///./pilot.db python scripts/seed_pilot_data.py

    # Against a real PostgreSQL deployment:
    DATABASE_URL=postgresql://user:pass@host/lumenai python scripts/seed_pilot_data.py

Environment variables:
    DATABASE_URL    — required
    TENANT_ID       — defaults to "bon-secours-pilot"
    DRY_RUN         — set to "1" to print plan without writing

Security notes:
    - No PHI is seeded. All names are facility/instrument identifiers only.
    - All AI outputs carry human_review_required=True.
    - Tenant isolation enforced — all rows scoped to TENANT_ID.
"""
from __future__ import annotations

import os
import random
from datetime import datetime, timedelta, timezone

TENANT_ID = os.getenv("TENANT_ID", "bon-secours-pilot")
TENANT_NAME = os.getenv("TENANT_NAME", "Bon Secours Pilot")
DRY_RUN = os.getenv("DRY_RUN", "0").strip() in {"1", "true", "yes"}

# ---------------------------------------------------------------------------
# Pilot instrument catalogue — 10 lumened instruments
# ---------------------------------------------------------------------------

INSTRUMENTS = [
    {
        "instrument_category": "flexible_ureteroscope",
        "manufacturer_name": "Olympus",
        "model_name": "URF-V3",
        "serial_number": "OLY-FU-00101",
        "barcode": "BS-FURO-001",
        "qr_code": "QR-BS-FURO-001",
        "udi": "(01)00888563170018(21)00101",
        "keydot_id": "KD-A1B2C3",
        "internal_id": "FURO-001",
        "max_cycle_count": 500,
    },
    {
        "instrument_category": "flexible_ureteroscope",
        "manufacturer_name": "Olympus",
        "model_name": "URF-V3",
        "serial_number": "OLY-FU-00102",
        "barcode": "BS-FURO-002",
        "qr_code": "QR-BS-FURO-002",
        "udi": "(01)00888563170018(21)00102",
        "keydot_id": "KD-D4E5F6",
        "internal_id": "FURO-002",
        "max_cycle_count": 500,
    },
    {
        "instrument_category": "laparoscope",
        "manufacturer_name": "Storz",
        "model_name": "Hopkins II 30°",
        "serial_number": "STZ-LAP-00201",
        "barcode": "BS-LAPO-001",
        "qr_code": "QR-BS-LAPO-001",
        "udi": "(01)04063929024231(21)00201",
        "keydot_id": "KD-G7H8I9",
        "internal_id": "LAPO-001",
        "max_cycle_count": 1000,
    },
    {
        "instrument_category": "laparoscope",
        "manufacturer_name": "Storz",
        "model_name": "Hopkins II 0°",
        "serial_number": "STZ-LAP-00202",
        "barcode": "BS-LAPO-002",
        "qr_code": "QR-BS-LAPO-002",
        "udi": "(01)04063929024248(21)00202",
        "keydot_id": None,
        "internal_id": "LAPO-002",
        "max_cycle_count": 1000,
    },
    {
        "instrument_category": "cystoscope",
        "manufacturer_name": "Olympus",
        "model_name": "CYF-VH",
        "serial_number": "OLY-CYS-00301",
        "barcode": "BS-CYSO-001",
        "qr_code": "QR-BS-CYSO-001",
        "udi": "(01)00888563820038(21)00301",
        "keydot_id": "KD-J1K2L3",
        "internal_id": "CYSO-001",
        "max_cycle_count": 750,
    },
    {
        "instrument_category": "bronchoscope",
        "manufacturer_name": "Fujifilm",
        "model_name": "EB-590S",
        "serial_number": "FJF-BRO-00401",
        "barcode": "BS-BRON-001",
        "qr_code": "QR-BS-BRON-001",
        "udi": "(01)04977444101247(21)00401",
        "keydot_id": None,
        "internal_id": "BRON-001",
        "max_cycle_count": 600,
    },
    {
        "instrument_category": "hysteroscope",
        "manufacturer_name": "Bettocchi",
        "model_name": "5.0 Fr",
        "serial_number": "BET-HYS-00501",
        "barcode": "BS-HYST-001",
        "qr_code": None,
        "udi": None,
        "keydot_id": "KD-M4N5O6",
        "internal_id": "HYST-001",
        "max_cycle_count": 400,
    },
    {
        "instrument_category": "arthroscope",
        "manufacturer_name": "Arthrex",
        "model_name": "NanoScope",
        "serial_number": "ATX-ART-00601",
        "barcode": "BS-ARTH-001",
        "qr_code": "QR-BS-ARTH-001",
        "udi": "(01)08717647050147(21)00601",
        "keydot_id": None,
        "internal_id": "ARTH-001",
        "max_cycle_count": 800,
    },
    {
        "instrument_category": "colonoscope",
        "manufacturer_name": "Olympus",
        "model_name": "CF-HQ190L",
        "serial_number": "OLY-COL-00701",
        "barcode": "BS-COLO-001",
        "qr_code": "QR-BS-COLO-001",
        "udi": "(01)00888563510131(21)00701",
        "keydot_id": "KD-P7Q8R9",
        "internal_id": "COLO-001",
        "max_cycle_count": 500,
    },
    {
        "instrument_category": "nephroscope",
        "manufacturer_name": "Wolf",
        "model_name": "Compact 26Fr",
        "serial_number": "WLF-NEP-00801",
        "barcode": "BS-NEPH-001",
        "qr_code": None,
        "udi": None,
        "keydot_id": "KD-S1T2U3",
        "internal_id": "NEPH-001",
        "max_cycle_count": 600,
    },
]

# ---------------------------------------------------------------------------
# Baseline catalogue — 25 entries (2-3 per instrument)
# ---------------------------------------------------------------------------

BASELINE_TEMPLATES = [
    # (instrument_category, manufacturer_name, model_name, baseline_type, approval_status)
    ("flexible_ureteroscope", "Olympus", "URF-V3", "manufacturer", "approved"),
    ("flexible_ureteroscope", "Olympus", "URF-V3", "vendor", "approved"),
    ("flexible_ureteroscope", "Olympus", "URF-V3", "network_contributed", "pending"),
    ("laparoscope", "Storz", "Hopkins II 30°", "manufacturer", "approved"),
    ("laparoscope", "Storz", "Hopkins II 30°", "vendor", "approved"),
    ("laparoscope", "Storz", "Hopkins II 30°", "network_contributed", "pending"),
    ("laparoscope", "Storz", "Hopkins II 0°", "manufacturer", "approved"),
    ("laparoscope", "Storz", "Hopkins II 0°", "vendor", "pending"),
    ("cystoscope", "Olympus", "CYF-VH", "manufacturer", "approved"),
    ("cystoscope", "Olympus", "CYF-VH", "vendor", "approved"),
    ("cystoscope", "Olympus", "CYF-VH", "network_contributed", "pending"),
    ("bronchoscope", "Fujifilm", "EB-590S", "manufacturer", "approved"),
    ("bronchoscope", "Fujifilm", "EB-590S", "vendor", "approved"),
    ("bronchoscope", "Fujifilm", "EB-590S", "network_contributed", "pending"),
    ("hysteroscope", "Bettocchi", "5.0 Fr", "manufacturer", "approved"),
    ("hysteroscope", "Bettocchi", "5.0 Fr", "vendor", "pending"),
    ("arthroscope", "Arthrex", "NanoScope", "manufacturer", "approved"),
    ("arthroscope", "Arthrex", "NanoScope", "vendor", "approved"),
    ("arthroscope", "Arthrex", "NanoScope", "network_contributed", "pending"),
    ("colonoscope", "Olympus", "CF-HQ190L", "manufacturer", "approved"),
    ("colonoscope", "Olympus", "CF-HQ190L", "vendor", "approved"),
    ("colonoscope", "Olympus", "CF-HQ190L", "network_contributed", "pending"),
    ("nephroscope", "Wolf", "Compact 26Fr", "manufacturer", "approved"),
    ("nephroscope", "Wolf", "Compact 26Fr", "vendor", "approved"),
    ("nephroscope", "Wolf", "Compact 26Fr", "network_contributed", "pending"),
]

# ---------------------------------------------------------------------------
# Inspection distribution — 50 records
# Realistic finding mix for a pilot week:
#   clean (none)     40%  → 20
#   debris            20%  → 10
#   blood             15%  →  8
#   tissue            10%  →  5
#   corrosion          5%  →  3
#   bone               5%  →  2
#   crack              3%  →  1
#   insulation_damage  2%  →  1
# ---------------------------------------------------------------------------

FINDING_DISTRIBUTION = (
    ["none"] * 20 +
    ["debris"] * 10 +
    ["blood"] * 8 +
    ["tissue"] * 5 +
    ["corrosion"] * 3 +
    ["bone"] * 2 +
    ["crack"] * 1 +
    ["insulation_damage"] * 1
)

INSTRUMENT_TYPES_ALLOWED = [
    "laparoscopic_grasper", "retractor", "scissors", "needle_holder",
    "forceps", "trocar", "electrosurgical", "suction_irrigation",
    "clip_applier", "stapler", "other",
]

SITES = ["OR-1", "OR-2", "OR-3", "SPD-Decon", "SPD-Prep"]
VENDORS = ["Aesculap", "Medline", "Symmetry", "Sklar", "Integra"]


def _risk(issue: str, confidence: float) -> int:
    base = {
        "none": 5, "debris": 30, "blood": 55, "tissue": 45,
        "corrosion": 65, "bone": 50, "crack": 80, "insulation_damage": 75,
    }.get(issue, 20)
    return min(100, int(base + (confidence - 70) * 0.3))


def main() -> None:
    os.environ.setdefault("ENABLE_DEV_AUTH", "true")
    os.environ.setdefault("DEV_AUTH_TOKEN", "dev-token")

    from app.db.session import SessionLocal, engine
    from app.db.base import Base

    # Import all models so create_all registers every table
    import importlib
    for m in [
        "app.models.inspection", "app.models.baseline_library",
        "app.models.p25_infrastructure", "app.models.audit_log",
        "app.models.enterprise_quality",
    ]:
        try:
            importlib.import_module(m)
        except Exception:
            pass

    Base.metadata.create_all(bind=engine)

    from app.models.inspection import Inspection
    from app.models.baseline_library import BaselineLibraryEntry
    from app.models.p25_infrastructure import InstrumentDigitalIdentity

    if DRY_RUN:
        print("DRY RUN — no records will be written.\n")
        print(f"Would create: {len(INSTRUMENTS)} instruments, {len(BASELINE_TEMPLATES)} baselines, 50 inspections")
        return

    db = SessionLocal()
    now = datetime.now(timezone.utc)
    rng = random.Random(42)  # reproducible seed

    # ── 1. Instrument digital identities ──────────────────────────────────────
    print(f"Seeding {len(INSTRUMENTS)} instrument digital identity records…")
    inst_ids = []
    for spec in INSTRUMENTS:
        udi = spec.get("udi")
        keydot = spec.get("keydot_id")
        method = "udi" if udi else ("keydot" if keydot else "barcode")
        obj = InstrumentDigitalIdentity(
            tenant_id=TENANT_ID,
            instrument_category=spec["instrument_category"],
            manufacturer_name=spec["manufacturer_name"],
            model_name=spec["model_name"],
            serial_number=spec["serial_number"],
            barcode=spec["barcode"],
            qr_code=spec.get("qr_code"),
            udi=udi,
            keydot_id=keydot,
            internal_id=spec["internal_id"],
            max_cycle_count=spec["max_cycle_count"],
            lifecycle_status="active",
            identity_verified=bool(udi or keydot),
            verification_method=method,
            human_review_required=True,
            total_cycle_count=rng.randint(0, spec["max_cycle_count"] // 3),
        )
        db.add(obj)
        db.flush()
        inst_ids.append(obj.id)
    db.commit()
    print(f"  ✓ {len(INSTRUMENTS)} instruments created (IDs {inst_ids[0]}–{inst_ids[-1]})")

    # ── 2. Baseline library entries ────────────────────────────────────────────
    print(f"Seeding {len(BASELINE_TEMPLATES)} baseline library entries…")
    baseline_ids = []
    for i, (cat, mfr, model, btype, status) in enumerate(BASELINE_TEMPLATES):
        approved_at = (now - timedelta(days=rng.randint(1, 30))) if status == "approved" else None
        obj = BaselineLibraryEntry(
            instrument_category=cat,
            manufacturer_name=mfr,
            model_name=model,
            baseline_type=btype,
            baseline_version=f"1.{i % 3}",
            approval_status=status,
            approved_by="qa.reviewer@bonsecours.org" if status == "approved" else None,
            approved_at=approved_at,
            contributing_facilities=1 if btype != "network_contributed" else rng.randint(2, 5),
            governance_notes=f"Pilot baseline — {btype} submission. Human review required.",
        )
        db.add(obj)
        db.flush()
        baseline_ids.append(obj.id)
    db.commit()
    approved_count = sum(1 for _, _, _, _, s in BASELINE_TEMPLATES if s == "approved")
    print(f"  ✓ {len(BASELINE_TEMPLATES)} baselines created ({approved_count} approved, "
          f"{len(BASELINE_TEMPLATES) - approved_count} pending)")

    # ── 3. Inspection records ─────────────────────────────────────────────────
    print("Seeding 50 inspection records…")
    findings = FINDING_DISTRIBUTION[:]
    rng.shuffle(findings)
    insp_ids = []
    for i, issue in enumerate(findings):
        confidence = round(rng.uniform(62.0, 97.5), 1)
        stain = issue != "none"
        itype = rng.choice(INSTRUMENT_TYPES_ALLOWED)
        created = now - timedelta(days=rng.randint(0, 6), hours=rng.randint(0, 23), minutes=rng.randint(0, 59))
        obj = Inspection(
            tenant_id=TENANT_ID,
            tenant_name=TENANT_NAME,
            file_name=f"pilot_{TENANT_ID}_{i+1:03d}.jpg",
            instrument_type=itype,
            detected_issue=issue,
            stain_detected=stain,
            confidence=confidence,
            material_type=rng.choice(["stainless_steel", "titanium", "polymer"]),
            site_name=rng.choice(SITES),
            vendor_name=rng.choice(VENDORS),
            risk_score=_risk(issue, confidence),
            status="reviewed" if i < 35 else "queued",
            qa_review_status="reviewed" if i < 35 else "pending",
            qa_reviewer="spd.manager@bonsecours.org" if i < 35 else "",
            qa_review_notes="Human review completed." if i < 35 else "",
            qa_reviewed_at=created + timedelta(hours=2) if i < 35 else None,
            model_name="lumenai-pilot-v1",
            model_version="1.0.0",
            inference_timestamp=created + timedelta(minutes=rng.randint(1, 10)),
            inference_mode="deterministic-fallback",
            alert_status="resolved" if i < 30 else "open",
            created_at=created,
        )
        db.add(obj)
        db.flush()
        insp_ids.append(obj.id)
    db.commit()

    finding_counts = {f: findings.count(f) for f in set(findings)}
    print(f"  ✓ 50 inspections created (IDs {insp_ids[0]}–{insp_ids[-1]})")
    print(f"  Finding distribution: {finding_counts}")

    db.close()

    print("\n── Pilot data seed complete ──")
    print(f"  Tenant:      {TENANT_ID}")
    print(f"  Instruments: {len(INSTRUMENTS)}")
    print(f"  Baselines:   {len(BASELINE_TEMPLATES)} ({approved_count} approved)")
    print("  Inspections: 50")
    print("\nAll records carry human_review_required=True where applicable.")
    print("No PHI was seeded. All data is instrument/facility identifiers only.")


if __name__ == "__main__":
    main()
