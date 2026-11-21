"""P4.7.2 — trusted inference provenance (server-controlled, database-backed).

Problem this replaces
---------------------
P4.7.1 decided whether a stored CV record was verified model inference by
reading claims out of the record's own ``result_json`` (an ``evidence_class``
marker and a ``model_integrity.verified`` flag). Anything able to write a row —
a second code path, a script, a raw SQL insert — could therefore promote
invented findings to operational evidence.

What establishes trust now
--------------------------
A record is verified model inference only while ONE ``CVInferenceProvenance``
row refers to it and ALL of the following hold:

* the row is in the ``trusted`` state (not revoked);
* it names the same record id, inference id, tenant, provider and status;
* its seal verifies under the server's provenance key;
* the record's operational fields still hash to the digest that was sealed.

The seal is an HMAC-SHA256 keyed with ``LUMENAI_PROVENANCE_HMAC_KEY``. That key
lives in server configuration, never in the database and never in a request, so
write access to the database is not enough to mint or alter trusted provenance.

Fail-closed
-----------
* No key configured            -> provenance cannot be issued or verified.
* No approved artifact digest  -> provenance cannot be issued.
* No database session          -> provenance cannot be issued.
* Any error while verifying    -> not trusted.

What a seal does NOT show: that the model detects defects. It shows only that
this server ran an approved, integrity-verified artifact for this tenant and
that the stored record is the one it produced.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import app.db  # noqa: F401 - app.db must initialise before app.models (existing import cycle)
from app.models.cv_inference import CVInferenceProvenance, CVInferenceRecord

STATE_TRUSTED = "trusted"
STATE_REVOKED = "revoked"

KEY_ENV = "LUMENAI_PROVENANCE_HMAC_KEY"
KEY_ID_ENV = "LUMENAI_PROVENANCE_HMAC_KEY_ID"
MIN_KEY_LENGTH = 32
_SEAL_VERSION = 1

# Server configuration that names an APPROVED model artifact by its SHA-256.
# These are the same pins the providers verify before loading an artifact.
APPROVED_ARTIFACT_PIN_ENVS = (
    "LUMENAI_MODEL_SHA256",
    "CV_ONNX_CLASSIFIER_SHA256",
    "CV_ONNX_DETECTOR_SHA256",
)

# Execution statuses that can describe a completed inference run.
TRUSTABLE_STATUSES = frozenset({"success", "partial"})

# The record fields the seal covers. Workflow fields that change legitimately
# after the run (human review / annotation, later links) are deliberately absent.
_SEALED_RECORD_FIELDS = (
    "inference_id", "tenant_id", "facility_id", "context", "provider", "status",
    "image_url", "baseline_image_url",
    "instrument_recognized", "instrument_name", "instrument_category",
    "instrument_confidence", "match_method",
    "barcode_value", "qr_value", "key_dot_value",
    "contamination_score", "damage_score", "overall_cleanliness_score",
    "baseline_compared", "baseline_match_pct", "baseline_verdict",
    "finding_count", "blood_count", "bone_count", "tissue_count", "corrosion_count",
    "crack_count", "insulation_count", "residue_count",
    "archived_image_key",
)
_HEX = frozenset("0123456789abcdef")
# Mirrors app.cv.evidence: these providers never produce model inference.
_NEVER_INFERENCE_PROVIDERS = frozenset({"mock", "unavailable"})


class ProvenanceError(RuntimeError):
    """Trusted provenance could not be issued. Callers must fail closed."""


@dataclass(frozen=True)
class ProvenanceCheck:
    trusted: bool
    reason: str  # stable, non-sensitive category


def _is_sha256(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return len(text) == 64 and set(text) <= _HEX


def _signing_key() -> tuple[str, bytes]:
    """The server's provenance key. Raises ``ProvenanceError`` when unusable."""
    key = os.getenv(KEY_ENV, "")
    if len(key.strip()) < MIN_KEY_LENGTH:
        raise ProvenanceError(
            f"No usable provenance key is configured ({KEY_ENV} must be at least "
            f"{MIN_KEY_LENGTH} characters)."
        )
    key_id = os.getenv(KEY_ID_ENV, "").strip() or "default"
    return key_id, key.encode("utf-8")


def provenance_key_configured() -> bool:
    try:
        _signing_key()
    except ProvenanceError:
        return False
    return True


def approved_artifact_digests() -> frozenset[str]:
    """SHA-256 digests the server configuration currently approves."""
    return frozenset(
        value.strip().lower()
        for value in (os.getenv(name, "") for name in APPROVED_ARTIFACT_PIN_ENVS)
        if _is_sha256(value)
    )


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def record_digest(record: CVInferenceRecord) -> str:
    """SHA-256 over the record's operational fields and its stored payload."""
    fields = {name: getattr(record, name, None) for name in _SEALED_RECORD_FIELDS}
    fields["result_json_sha256"] = hashlib.sha256(
        (record.result_json or "").encode("utf-8")
    ).hexdigest()
    return hashlib.sha256(_canonical(fields).encode("utf-8")).hexdigest()


def _seal(row: CVInferenceProvenance, key: bytes) -> str:
    payload = _canonical({
        "v": _SEAL_VERSION,
        "state": row.state,
        "record_id": row.record_id,
        "inference_id": row.inference_id,
        "tenant_id": row.tenant_id,
        "provider": row.provider,
        "execution_status": row.execution_status,
        "model_versions": row.model_versions_json,
        "artifact_digests": row.artifact_digests_json,
        "record_digest": row.record_digest,
        "key_id": row.key_id,
        "issued_at": row.issued_at,
        "revoked_at": row.revoked_at or "",
    })
    return hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def _validated_artifacts(artifacts: dict[str, str] | None) -> dict[str, str]:
    """Every artifact digest must be well-formed AND currently approved."""
    cleaned = {
        str(name): str(digest).strip().lower()
        for name, digest in (artifacts or {}).items()
    }
    if not cleaned:
        raise ProvenanceError("The provider reported no integrity-verified model artifact.")
    approved = approved_artifact_digests()
    for name, digest in cleaned.items():
        if not _is_sha256(digest):
            raise ProvenanceError(f"Artifact '{name}' has no valid SHA-256 digest.")
        if digest not in approved:
            raise ProvenanceError(f"Artifact '{name}' is not an approved model artifact.")
    return cleaned


def assert_issuable(db: Session | None, artifacts: dict[str, str] | None) -> None:
    """Pre-flight: raise ``ProvenanceError`` unless provenance could be issued now.

    Lets the pipeline decide to withhold a result BEFORE it archives anything."""
    if db is None:
        raise ProvenanceError("Trusted provenance requires a database session.")
    _signing_key()
    _validated_artifacts(artifacts)


def issue_provenance(
    db: Session,
    record: CVInferenceRecord,
    *,
    authenticated_tenant_id: str,
    artifacts: dict[str, str],
    model_versions: dict[str, str] | None = None,
) -> CVInferenceProvenance:
    """Seal ONE completed inference run. Server pipeline only; does not commit.

    ``record`` must already be flushed (it needs its id). Raises
    ``ProvenanceError`` on anything that prevents a truthful seal."""
    if record.id is None:
        raise ProvenanceError("The inference record must be persisted before it can be sealed.")
    tenant = str(authenticated_tenant_id or "").strip()
    if not tenant or tenant != str(record.tenant_id or ""):
        raise ProvenanceError("The record's tenant is not the authenticated tenant of this run.")
    if str(record.status or "") not in TRUSTABLE_STATUSES:
        raise ProvenanceError("Only a completed inference run can be sealed.")
    if str(record.provider or "").strip().lower() in _NEVER_INFERENCE_PROVIDERS:
        raise ProvenanceError("A simulated or unavailable provider's output cannot be sealed.")
    key_id, key = _signing_key()
    cleaned = _validated_artifacts(artifacts)
    # Seal the values the database actually stored (e.g. 50 -> 50.0), so the
    # digest recomputed from a later read is the same.
    db.refresh(record)

    row = CVInferenceProvenance(
        record_id=record.id,
        inference_id=record.inference_id,
        tenant_id=tenant,
        provider=str(record.provider or ""),
        execution_status=str(record.status or ""),
        model_versions_json=_canonical(model_versions or {}),
        artifact_digests_json=_canonical(cleaned),
        record_digest=record_digest(record),
        state=STATE_TRUSTED,
        key_id=key_id,
        issued_at=datetime.now(timezone.utc).isoformat(),
        revoked_at="", revoked_by="", revoked_reason="",
    )
    row.attestation = _seal(row, key)
    db.add(row)
    db.flush()
    return row


def _check(record: CVInferenceRecord, row: CVInferenceProvenance | None) -> ProvenanceCheck:
    if row is None:
        return ProvenanceCheck(False, "no_provenance")
    if str(row.state or "") != STATE_TRUSTED or str(row.revoked_at or ""):
        return ProvenanceCheck(False, "provenance_revoked")
    if row.record_id != record.id or row.inference_id != record.inference_id:
        return ProvenanceCheck(False, "provenance_record_mismatch")
    if str(row.tenant_id or "") != str(record.tenant_id or ""):
        return ProvenanceCheck(False, "provenance_tenant_mismatch")
    if row.provider != record.provider or row.execution_status != record.status:
        return ProvenanceCheck(False, "provenance_run_mismatch")
    if str(record.status or "") not in TRUSTABLE_STATUSES:
        return ProvenanceCheck(False, "run_not_completed")
    try:
        artifacts = json.loads(row.artifact_digests_json or "{}")
    except (TypeError, ValueError):
        return ProvenanceCheck(False, "provenance_malformed")
    if not isinstance(artifacts, dict) or not artifacts or not all(
        _is_sha256(digest) for digest in artifacts.values()
    ):
        return ProvenanceCheck(False, "provenance_malformed")
    try:
        key_id, key = _signing_key()
    except ProvenanceError:
        return ProvenanceCheck(False, "provenance_key_unavailable")
    if row.key_id != key_id:
        return ProvenanceCheck(False, "provenance_key_mismatch")
    if not hmac.compare_digest(str(row.attestation or ""), _seal(row, key)):
        return ProvenanceCheck(False, "provenance_seal_invalid")
    if not hmac.compare_digest(str(row.record_digest or ""), record_digest(record)):
        return ProvenanceCheck(False, "record_altered_after_sealing")
    return ProvenanceCheck(True, "trusted")


def verify_records(db: Session | None, records: Iterable[CVInferenceRecord]) -> dict[int, ProvenanceCheck]:
    """Verify many records with one provenance query. Never raises: any failure
    to read provenance leaves every record untrusted."""
    records = [r for r in records if r is not None and r.id is not None]
    untrusted = {r.id: ProvenanceCheck(False, "no_provenance") for r in records}
    if db is None or not records:
        return untrusted
    try:
        rows = (
            db.query(CVInferenceProvenance)
            .filter(CVInferenceProvenance.record_id.in_([r.id for r in records]))
            .all()
        )
    except SQLAlchemyError:
        db.rollback()
        return {r.id: ProvenanceCheck(False, "provenance_unreadable") for r in records}
    by_record: dict[int, list[CVInferenceProvenance]] = {}
    for row in rows:
        by_record.setdefault(row.record_id, []).append(row)
    checks: dict[int, ProvenanceCheck] = {}
    for record in records:
        candidates = by_record.get(record.id, [])
        if len(candidates) > 1:  # the unique constraint was bypassed
            checks[record.id] = ProvenanceCheck(False, "provenance_ambiguous")
        else:
            checks[record.id] = _check(record, candidates[0] if candidates else None)
    return checks


def verify_record(db: Session | None, record: CVInferenceRecord) -> ProvenanceCheck:
    if record is None or record.id is None:
        return ProvenanceCheck(False, "no_provenance")
    return verify_records(db, [record])[record.id]


def provenance_summary(db: Session | None, record: CVInferenceRecord) -> dict[str, Any]:
    """The server-verified integrity view of a record, safe to return to a client.

    Built from the provenance row — never from the record's own stored claims."""
    check = verify_record(db, record)
    if not check.trusted:
        return {"verified": False, "reason": check.reason}
    row = db.query(CVInferenceProvenance).filter(CVInferenceProvenance.record_id == record.id).first()
    return {
        "verified": True,
        "artifacts": json.loads(row.artifact_digests_json),
        "issued_at": row.issued_at,
    }


def revoke_provenance(
    db: Session, *, inference_id: str, tenant_id: str, revoked_by: str, reason: str,
) -> bool:
    """Revoke one run's provenance (server/governance action). Does not commit.

    The row is re-sealed in the ``revoked`` state, so it cannot be returned to
    ``trusted`` by editing columns. Returns ``False`` when there was nothing to revoke."""
    row = (
        db.query(CVInferenceProvenance)
        .filter(
            CVInferenceProvenance.inference_id == inference_id,
            CVInferenceProvenance.tenant_id == tenant_id,
        )
        .first()
    )
    if row is None or row.state != STATE_TRUSTED:
        return False
    _key_id, key = _signing_key()
    row.state = STATE_REVOKED
    row.revoked_at = datetime.now(timezone.utc).isoformat()
    row.revoked_by = str(revoked_by or "")[:255]
    row.revoked_reason = str(reason or "")[:255]
    row.attestation = _seal(row, key)
    db.flush()
    return True


def revoke_provenance_for_artifact(db: Session, *, sha256: str, revoked_by: str, reason: str) -> int:
    """Revoke every run sealed with a given artifact digest (e.g. a withdrawn
    model). Does not commit. Returns the number of runs revoked."""
    digest = str(sha256 or "").strip().lower()
    if not _is_sha256(digest):
        return 0
    revoked = 0
    rows = (
        db.query(CVInferenceProvenance)
        .filter(
            CVInferenceProvenance.state == STATE_TRUSTED,
            CVInferenceProvenance.artifact_digests_json.contains(digest, autoescape=True),
        )
        .all()
    )
    for row in rows:
        if revoke_provenance(
            db, inference_id=row.inference_id, tenant_id=row.tenant_id,
            revoked_by=revoked_by, reason=reason,
        ):
            revoked += 1
    return revoked
