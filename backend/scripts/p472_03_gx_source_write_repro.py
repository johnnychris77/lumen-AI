#!/usr/bin/env python3
"""P472-03 Batch 7 — reproduce GuardianX foreign-source writes and their downstream effect.

Runs entirely against a LOCAL database named by DATABASE_URL (refuses to run
without one, or with APP_ENV=production). Uses only HTTP routes that exist both
before and after the Batch 7 source-ownership change, so a reviewer can run it
at either SHA and compare. Prints one JSON document.

  cd backend && DATABASE_URL=sqlite:////tmp/gx.db python scripts/p472_03_gx_source_write_repro.py
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
from app.models.guardianx_assurance import EvidenceLedgerEntry  # noqa: E402
from app.models.inspection import Inspection  # noqa: E402
from app.models.user_role_assignment import UserRoleAssignment  # noqa: E402
from app.routers.auth_simple import _make_token  # noqa: E402
from app.services import guardianx_ledger_ownership as ownership  # noqa: E402

RUN = uuid.uuid4().hex[:8]
TA, TB = f"gxw-a-{RUN}", f"gxw-b-{RUN}"
UA, UB = f"gxw-a-{RUN}@example.test", f"gxw-b-{RUN}@example.test"
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


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    for user, tenant in ((UA, TA), (UB, TB)):
        db.add(UserRoleAssignment(username=user, role="admin", assigned_by="p472-03-b7-repro"))
        db.add(models.TenantMembership(tenant_id=tenant, user_email=user, role="admin", is_enabled=True))
    insp = Inspection(file_name="b7-repro.png", tenant_id=TA)
    db.add(insp)
    db.commit()
    insp_id = str(insp.id)
    db.close()

    capa_key = f"capa-{RUN}"
    out = {"tenants": {"A": TA, "B": TB}, "inspection_of_A": insp_id, "writes": {}, "downstream": {}}
    ev = "/api/guardianx/evidence"
    out["writes"]["A_ledger_own_inspection"] = call("POST", ev, UA, TA, json={
        "source_type": "inspection", "source_id": insp_id, "evidence": ["a-own-evidence"]})["status"]
    out["writes"]["A_ledger_own_capa_key"] = call("POST", ev, UA, TA, json={
        "source_type": "capa_suggestion", "source_id": capa_key, "evidence": ["a-capa-evidence"]})["status"]
    out["writes"]["B_ledger_into_A_inspection"] = call("POST", ev, UB, TB, json={
        "source_type": "inspection", "source_id": insp_id, "evidence": ["injected-by-B"]})
    out["writes"]["B_ledger_into_A_capa_key"] = call("POST", ev, UB, TB, json={
        "source_type": "capa_suggestion", "source_id": capa_key, "evidence": ["injected-by-B-capa"]})
    out["writes"]["B_ledger_nonexistent_inspection"] = call("POST", ev, UB, TB, json={
        "source_type": "inspection", "source_id": "999999999", "evidence": ["x"]})["status"]
    out["writes"]["B_explanation_into_A_inspection"] = call("POST", "/api/guardianx/explainability", UB, TB, json={
        "source_type": "inspection", "source_id": insp_id, "input_summary": "injected-explanation-by-B"})
    out["writes"]["A_explanation_own_inspection"] = call("POST", "/api/guardianx/explainability", UA, TA, json={
        "source_type": "inspection", "source_id": insp_id, "input_summary": "a-private-explanation"})
    dt = call("POST", "/api/guardianx/explainability", UB, TB, json={
        "source_type": "capa_suggestion", "source_id": f"dt-{RUN}", "tenant_id_for_digital_twin": TA})
    out["writes"]["B_explanation_digital_twin_claim_for_A"] = {
        "status": dt["status"],
        "digital_twin_context_returned": bool(isinstance(dt["body"], dict) and dt["body"].get("digital_twin_context")),
        "detail": dt["body"].get("detail") if isinstance(dt["body"], dict) else None}

    db = SessionLocal()
    rows = db.query(EvidenceLedgerEntry).filter(EvidenceLedgerEntry.source_id.in_([insp_id, capa_key])).all()
    out["persisted_ledger_rows"] = [{"id": r.id, "source": f"{r.source_type}:{r.source_id}",
                                     "evidence": json.loads(r.evidence_json), "reviewer": r.reviewer,
                                     "audit_owner_tenant": ownership.audit_owner_tenant(db, r.id)} for r in rows]
    classified = {c["entry_id"]: c for c in ownership.classify_entries(db)}
    out["dry_run_classification_of_these_rows"] = {r.id: {k: classified[r.id].get(k) for k in
                                                            ("classification", "reason", "tenant_id")}
                                                   for r in rows if r.id in classified}
    db.close()

    def texts(resp):
        return json.dumps(resp["body"])
    d = out["downstream"]
    a_list = call("GET", ev, UA, TA, params={"source_type": "inspection", "source_id": insp_id})
    d["A_list_inspection_contains_injected"] = "injected-by-B" in texts(a_list)
    b_list = call("GET", ev, UB, TB, params={"source_type": "inspection", "source_id": insp_id})
    d["B_list_inspection_contains_injected"] = "injected-by-B" in texts(b_list)
    rep = call("GET", f"/api/guardianx/audit-replay/inspections/{insp_id}", UA, TA)
    d["A_inspection_replay_status"] = rep["status"]
    d["A_inspection_replay_contains_injected_evidence"] = "injected-by-B" in texts(rep)
    d["A_inspection_replay_contains_injected_explanation"] = "injected-explanation-by-B" in texts(rep)
    rec = call("GET", "/api/guardianx/audit-replay/recommendations", UA, TA,
               params={"source_type": "inspection", "source_id": insp_id})
    d["A_recommendation_replay_contains_injected_explanation"] = "injected-explanation-by-B" in texts(rec)
    b_rec = call("GET", "/api/guardianx/audit-replay/recommendations", UB, TB,
                 params={"source_type": "inspection", "source_id": insp_id})
    d["B_recommendation_replay_contains_A_private_explanation"] = "a-private-explanation" in texts(b_rec)
    pkg = call("GET", "/api/guardianx/reports/audit-evidence-package", UB, TB,
               params={"source_type": "inspection", "source_id": insp_id})
    d["B_audit_evidence_package_status"] = pkg["status"]
    d["B_audit_evidence_package_contains_A_private_explanation"] = "a-private-explanation" in texts(pkg)
    d["B_audit_evidence_package_ledger_entries"] = (len(pkg["body"].get("replay", {}).get("evidence_ledger", []))
                                                    if isinstance(pkg["body"], dict) else None)
    b_expl = call("GET", "/api/guardianx/explainability", UB, TB,
                  params={"source_type": "inspection", "source_id": insp_id})
    d["B_explainability_list_status"] = b_expl["status"]
    d["B_explainability_list_contains_A_private_explanation"] = "a-private-explanation" in texts(b_expl)
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
