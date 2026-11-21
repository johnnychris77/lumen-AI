#!/usr/bin/env python3
"""P472-03 Batch 8 — reproduce GuardianX explanation disclosure and foreign writes (RB-T32 / GX-09..GX-12).

Runs only against a LOCAL throw-away database named by DATABASE_URL. It refuses to
run without one, or with APP_ENV=production. It uses only HTTP routes that exist
both before and after the Batch 8 change, so a reviewer can run it at either SHA
and compare. Prints one JSON document; no PHI (synthetic ids, example.test users).

  cd backend && DATABASE_URL=sqlite:////tmp/gx8.db python scripts/p472_03_gx_explanation_repro.py
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

if not os.environ.get("DATABASE_URL") or os.environ.get("APP_ENV", "").lower() in {"production", "prod"}:
    sys.exit("refusing: set DATABASE_URL to a local throw-away database (never production)")
os.environ.setdefault("APP_ENV", "test")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.db import models  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.audit_log import AuditLog  # noqa: E402
from app.models.guardianx_assurance import AIExplainabilityRecord  # noqa: E402
from app.models.inspection import Inspection  # noqa: E402
from app.models.user_role_assignment import UserRoleAssignment  # noqa: E402
from app.routers.auth_simple import _make_token  # noqa: E402

RUN = uuid.uuid4().hex[:8]
TA, TB = f"gxe-a-{RUN}", f"gxe-b-{RUN}"
UA, UB = f"gxe-a-{RUN}@example.test", f"gxe-b-{RUN}@example.test"
EXPLAIN = "/api/guardianx/explainability"
client = TestClient(app, raise_server_exceptions=False)


def h(user, tenant):
    return {"Authorization": f"Bearer {_make_token(user)}", "X-Tenant-Id": tenant}


def call(method, path, user, tenant, **kw):
    r = client.request(method, path, headers=h(user, tenant), **kw)
    try:
        body = r.json()
    except ValueError:
        body = r.text[:300]
    return {"status": r.status_code, "body": body}


def leaks(response: dict, marker: str) -> bool:
    return marker in json.dumps(response["body"])


def row(record_id: int) -> dict | None:
    db = SessionLocal()
    try:
        r = db.query(AIExplainabilityRecord).filter(AIExplainabilityRecord.id == record_id).first()
        return None if r is None else {"created_by": r.created_by, "human_overrides": json.loads(r.human_overrides_json)}
    finally:
        db.close()


def audit_tenants(record_id: int) -> list[str]:
    db = SessionLocal()
    try:
        return sorted({t or "" for (t,) in db.query(AuditLog.tenant_id).filter(
            AuditLog.resource_type == "guardianx_explainability_record",
            AuditLog.resource_id == str(record_id)).all()})
    finally:
        db.close()


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    for user, tenant in ((UA, TA), (UB, TB)):
        db.add(UserRoleAssignment(username=user, role="admin", assigned_by="p472-03-b8-repro"))
        db.add(models.TenantMembership(tenant_id=tenant, user_email=user, role="admin", is_enabled=True))
    insp = Inspection(file_name=f"b8-{RUN}.png", tenant_id=TA)
    db.add(insp)
    db.commit()
    inspection_id = insp.id
    db.close()

    key = f"capa-{RUN}"
    secret_key, secret_insp = f"private-{key}", f"private-insp-{RUN}"
    a_key = call("POST", EXPLAIN, UA, TA, json={"source_type": "capa_suggestion", "source_id": key,
                                                 "input_summary": secret_key})
    a_insp = call("POST", EXPLAIN, UA, TA, json={"source_type": "inspection", "source_id": str(inspection_id),
                                                  "input_summary": secret_insp})
    key_id, insp_id = a_key["body"].get("id"), a_insp["body"].get("id")
    q = {"source_type": "capa_suggestion", "source_id": key}

    out: dict = {"tenant_a_writes": {"ownerless_key": a_key["status"], "own_inspection": a_insp["status"]},
                 "audit_events_for_a_explanation": audit_tenants(key_id) if key_id else None}
    reads = {
        "B list by source": call("GET", EXPLAIN, UB, TB, params=q),
        "B get by id": call("GET", f"{EXPLAIN}/{key_id}", UB, TB),
        "B recommendation replay": call("GET", "/api/guardianx/audit-replay/recommendations", UB, TB, params=q),
        "B audit-evidence package": call("GET", "/api/guardianx/reports/audit-evidence-package", UB, TB, params=q),
        "B get A's inspection explanation by id": call("GET", f"{EXPLAIN}/{insp_id}", UB, TB),
    }
    out["cross_tenant_reads"] = {name: {"status": r["status"],
                                        "discloses_a_private_text": leaks(r, secret_key) or leaks(r, secret_insp)}
                                 for name, r in reads.items()}
    # A foreign WRITE into A's explanation by id (human override).
    override = call("POST", f"{EXPLAIN}/{key_id}/human-override", UB, TB, json={"override_note": f"b-{RUN}"})
    out["b_override_on_a_explanation"] = {"status": override["status"], "persisted_row": row(key_id)}
    # B writes its own explanation under A's ownerless key: does it surface in A's view?
    b_into_key = call("POST", EXPLAIN, UB, TB, json={"source_type": "capa_suggestion", "source_id": key,
                                                      "input_summary": f"injected-{RUN}"})
    a_view = call("GET", EXPLAIN, UA, TA, params=q)
    out["b_explanation_into_a_key"] = {"status": b_into_key["status"],
                                       "visible_in_a_list": leaks(a_view, f"injected-{RUN}")}
    # Audit chain of A's inspection through B's generic replay (resource chosen by the caller).
    chain = call("GET", "/api/guardianx/audit-replay/recommendations", UB, TB,
                 params={"source_type": "inspection", "source_id": str(inspection_id)})
    out["b_reads_chain_of_a_inspection"] = {"status": chain["status"],
                                            "audit_chain": (chain["body"] or {}).get("audit_chain")
                                            if isinstance(chain["body"], dict) else None}
    # Same-tenant controls.
    out["controls"] = {
        "A list own key": leaks(call("GET", EXPLAIN, UA, TA, params=q), secret_key),
        "A get own by id": call("GET", f"{EXPLAIN}/{key_id}", UA, TA)["status"],
        "A override own": call("POST", f"{EXPLAIN}/{key_id}/human-override", UA, TA,
                               json={"override_note": "own"})["status"],
        "A inspection replay shows own explanation": leaks(
            call("GET", f"/api/guardianx/audit-replay/inspections/{inspection_id}", UA, TA), secret_insp),
    }
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
