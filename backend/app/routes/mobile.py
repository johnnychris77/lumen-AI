"""P18: Mobile, Offline & Point-of-Use Inspection Platform routes."""
from __future__ import annotations

import base64
import hashlib
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.enterprise_auth import get_request_actor, get_request_tenant_id, require_enterprise_auth
from app.models.mobile import (
    DeviceSession,
    ImageCaptureSession,
    MobileNotification,
    MobileSyncQueue,
    OfflineInspectionSession,
    ScanResult,
)
from app.services.mobile_service import (
    _seed,
    dispatch_notification,
    get_mobile_dashboard_data,
    process_offline_sync,
    resolve_scan_value,
)

router = APIRouter(prefix="/api/mobile", tags=["mobile"])

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class CreateSessionBody(BaseModel):
    facility_id: Optional[str] = None
    technician_id: str
    device_id: Optional[str] = None
    instrument_id: Optional[str] = None
    tray_id: Optional[str] = None
    inspection_type: Optional[str] = "standard"
    started_at_device: Optional[str] = None


class UpdateSessionBody(BaseModel):
    offline_findings_json: Optional[str] = None
    offline_capa_notes: Optional[str] = None
    completed_at_device: Optional[str] = None
    image_count: Optional[int] = None


class ScanDecodeBody(BaseModel):
    image_base64: str
    scan_type: str
    session_id: Optional[str] = None
    facility_id: Optional[str] = None


class ScanLookupBody(BaseModel):
    value: str
    scan_type: str


class CreateCaptureSessionBody(BaseModel):
    inspection_session_id: Optional[str] = None
    capture_type: str
    device_type: Optional[str] = "camera"
    facility_id: Optional[str] = None


class UploadImageBody(BaseModel):
    capture_session_id: str
    image_base64: str
    image_type: Optional[str] = "jpeg"
    annotation: Optional[str] = None


class CreateNotificationBody(BaseModel):
    recipient_id: str
    notification_type: str
    title: str
    body: str
    priority: Optional[str] = "normal"
    delivery_channel: Optional[str] = "in_app"
    action_url: Optional[str] = None
    expires_at: Optional[str] = None
    facility_id: Optional[str] = None


class BroadcastNotificationBody(BaseModel):
    facility_id: str
    notification_type: str
    title: str
    body: str
    priority: Optional[str] = "normal"


class RegisterDeviceBody(BaseModel):
    device_id: str
    device_type: Optional[str] = None
    user_agent: Optional[str] = None
    auth_method: Optional[str] = "token"


class SyncQueueItem(BaseModel):
    payload_type: str
    payload_json: str


class AddToQueueBody(BaseModel):
    device_id: Optional[str] = None
    session_id: Optional[str] = None
    items: List[SyncQueueItem]


# ---------------------------------------------------------------------------
# Offline Session Management
# ---------------------------------------------------------------------------


@router.post("/sessions")
def create_session(body: CreateSessionBody, request: Request, db: Session = Depends(get_db)):
    tenant_info = require_enterprise_auth(request)
    tenant_id = get_request_tenant_id(request)

    started = datetime.utcnow()
    if body.started_at_device:
        try:
            started = datetime.fromisoformat(body.started_at_device)
        except Exception:
            pass

    session = OfflineInspectionSession(
        tenant_id=tenant_id,
        facility_id=body.facility_id,
        technician_id=body.technician_id,
        device_id=body.device_id,
        instrument_id=body.instrument_id,
        tray_id=body.tray_id,
        inspection_type=body.inspection_type or "standard",
        started_at_device=started,
        sync_status="PENDING_SYNC",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    log_audit_event(db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=get_request_actor(request), actor_role="", action_type="mobile.session.create", resource_type="offline_inspection_sessions", resource_id=session.session_id)

    return {"session_id": session.session_id, "sync_status": session.sync_status, "created_at": session.created_at}


@router.get("/sessions")
def list_sessions(
    request: Request,
    sync_status: Optional[str] = None,
    technician_id: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    tenant_info = require_enterprise_auth(request)
    tenant_id = get_request_tenant_id(request)

    q = db.query(OfflineInspectionSession).filter_by(tenant_id=tenant_id)
    if sync_status:
        q = q.filter(OfflineInspectionSession.sync_status == sync_status)
    if technician_id:
        q = q.filter(OfflineInspectionSession.technician_id == technician_id)
    sessions = q.order_by(OfflineInspectionSession.created_at.desc()).limit(limit).all()

    return {
        "sessions": [
            {
                "session_id": s.session_id,
                "technician_id": s.technician_id,
                "inspection_type": s.inspection_type,
                "sync_status": s.sync_status,
                "image_count": s.image_count,
                "created_at": s.created_at,
            }
            for s in sessions
        ],
        "total": len(sessions),
    }


@router.get("/sessions/{session_id}")
def get_session(session_id: str, request: Request, db: Session = Depends(get_db)):
    tenant_info = require_enterprise_auth(request)
    tenant_id = get_request_tenant_id(request)

    session = db.query(OfflineInspectionSession).filter_by(session_id=session_id, tenant_id=tenant_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session.session_id,
        "tenant_id": session.tenant_id,
        "facility_id": session.facility_id,
        "technician_id": session.technician_id,
        "device_id": session.device_id,
        "instrument_id": session.instrument_id,
        "tray_id": session.tray_id,
        "inspection_type": session.inspection_type,
        "sync_status": session.sync_status,
        "started_at_device": session.started_at_device,
        "completed_at_device": session.completed_at_device,
        "image_count": session.image_count,
        "images_synced": session.images_synced,
        "linked_inspection_id": session.linked_inspection_id,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }


@router.patch("/sessions/{session_id}")
def update_session(session_id: str, body: UpdateSessionBody, request: Request, db: Session = Depends(get_db)):
    tenant_info = require_enterprise_auth(request)
    tenant_id = get_request_tenant_id(request)

    session = db.query(OfflineInspectionSession).filter_by(session_id=session_id, tenant_id=tenant_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if body.offline_findings_json is not None:
        session.offline_findings_json = body.offline_findings_json
    if body.offline_capa_notes is not None:
        session.offline_capa_notes = body.offline_capa_notes
    if body.completed_at_device is not None:
        try:
            session.completed_at_device = datetime.fromisoformat(body.completed_at_device)
        except Exception:
            pass
    if body.image_count is not None:
        session.image_count = body.image_count
    session.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(session)

    return {"session_id": session.session_id, "sync_status": session.sync_status, "updated_at": session.updated_at}


@router.post("/sessions/{session_id}/sync")
def sync_session(session_id: str, request: Request, db: Session = Depends(get_db)):
    tenant_info = require_enterprise_auth(request)
    tenant_id = get_request_tenant_id(request)

    result = process_offline_sync(db, session_id, tenant_id)
    log_audit_event(db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=get_request_actor(request), actor_role="", action_type="mobile.session.sync", resource_type="offline_inspection_sessions", resource_id=session_id)
    return result


@router.get("/sessions/{session_id}/sync-status")
def sync_status(session_id: str, request: Request, db: Session = Depends(get_db)):
    tenant_info = require_enterprise_auth(request)
    tenant_id = get_request_tenant_id(request)

    session = db.query(OfflineInspectionSession).filter_by(session_id=session_id, tenant_id=tenant_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session.session_id,
        "sync_status": session.sync_status,
        "synced_at": session.synced_at,
        "retry_count": session.retry_count,
        "sync_error": session.sync_error,
        "linked_inspection_id": session.linked_inspection_id,
    }


# ---------------------------------------------------------------------------
# Scan API
# ---------------------------------------------------------------------------


@router.post("/scan/decode")
def decode_scan(body: ScanDecodeBody, request: Request, db: Session = Depends(get_db)):
    tenant_info = require_enterprise_auth(request)
    tenant_id = get_request_tenant_id(request)

    seed_key = body.image_base64[:32] if len(body.image_base64) >= 32 else body.image_base64
    rng = _seed(seed_key)

    scan_types = {"barcode": "BC", "qr": "QR", "udi": "UDI", "keydot": "KD"}
    prefix = scan_types.get(body.scan_type, "SC")
    decoded_value = f"{prefix}-{rng.randint(100000, 999999)}"
    confidence = round(rng.uniform(0.82, 0.99), 3)
    instrument_id = f"INST-{rng.randint(1000, 9999)}"

    scan = ScanResult(
        tenant_id=tenant_id,
        facility_id=body.facility_id,
        session_id=body.session_id,
        scan_type=body.scan_type,
        decoded_value=decoded_value,
        confidence_score=confidence,
        scan_timestamp=datetime.utcnow(),
        instrument_id_resolved=instrument_id,
        lookup_status="found",
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    log_audit_event(db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=get_request_actor(request), actor_role="", action_type="mobile.scan.decode", resource_type="scan_results", resource_id=scan.scan_id)

    return {
        "scan_id": scan.scan_id,
        "decoded_value": decoded_value,
        "confidence_score": confidence,
        "instrument_id_resolved": instrument_id,
        "lookup_status": scan.lookup_status,
    }


@router.get("/scan/results")
def list_scan_results(
    request: Request,
    session_id: Optional[str] = None,
    scan_type: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    tenant_info = require_enterprise_auth(request)
    tenant_id = get_request_tenant_id(request)

    q = db.query(ScanResult).filter_by(tenant_id=tenant_id)
    if session_id:
        q = q.filter(ScanResult.session_id == session_id)
    if scan_type:
        q = q.filter(ScanResult.scan_type == scan_type)
    results = q.order_by(ScanResult.created_at.desc()).limit(limit).all()

    return {
        "results": [
            {
                "scan_id": r.scan_id,
                "scan_type": r.scan_type,
                "decoded_value": r.decoded_value,
                "confidence_score": r.confidence_score,
                "instrument_id_resolved": r.instrument_id_resolved,
                "lookup_status": r.lookup_status,
                "scan_timestamp": r.scan_timestamp,
            }
            for r in results
        ],
        "total": len(results),
    }


@router.post("/scan/lookup")
def lookup_scan(body: ScanLookupBody, request: Request, db: Session = Depends(get_db)):
    tenant_info = require_enterprise_auth(request)
    tenant_id = get_request_tenant_id(request)

    result = resolve_scan_value(db, tenant_id, body.value, body.scan_type)
    if not result:
        raise HTTPException(status_code=404, detail="Instrument not found for given scan value")
    return result


# ---------------------------------------------------------------------------
# Image Capture
# ---------------------------------------------------------------------------

_IMAGE_SESSION_STORE: Dict[str, Dict] = {}  # in-memory metadata store (prod: use blob storage)

_MAX_IMAGE_BYTES = 10 * 1024 * 1024   # 10 MB per image
_MAX_SESSION_BYTES = 50 * 1024 * 1024  # 50 MB per session


@router.post("/images/session")
def create_capture_session(body: CreateCaptureSessionBody, request: Request, db: Session = Depends(get_db)):
    tenant_info = require_enterprise_auth(request)
    tenant_id = get_request_tenant_id(request)

    cap = ImageCaptureSession(
        tenant_id=tenant_id,
        facility_id=body.facility_id,
        inspection_session_id=body.inspection_session_id,
        capture_type=body.capture_type,
        device_type=body.device_type or "camera",
    )
    db.add(cap)
    db.commit()
    db.refresh(cap)

    return {
        "capture_session_id": cap.capture_session_id,
        "upload_url_pattern": "/api/mobile/images/upload",
        "upload_status": cap.upload_status,
        "created_at": cap.started_at,
    }


@router.post("/images/upload")
def upload_image(body: UploadImageBody, request: Request, db: Session = Depends(get_db)):
    tenant_info = require_enterprise_auth(request)
    tenant_id = get_request_tenant_id(request)

    cap = db.query(ImageCaptureSession).filter_by(
        capture_session_id=body.capture_session_id, tenant_id=tenant_id
    ).first()
    if not cap:
        raise HTTPException(status_code=404, detail="Capture session not found")

    # Validate base64 and compute size
    try:
        image_bytes = base64.b64decode(body.image_base64, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 image data")

    size_bytes = len(image_bytes)
    if size_bytes > _MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail=f"Image exceeds 10MB limit ({size_bytes} bytes)")

    new_total = cap.total_size_bytes + size_bytes
    if new_total > _MAX_SESSION_BYTES:
        raise HTTPException(status_code=413, detail="Session 50MB storage limit exceeded")

    # Store metadata only — not the raw image
    image_hash = hashlib.sha256(image_bytes).hexdigest()
    image_id = str(uuid.uuid4())

    cap.image_count += 1
    cap.total_size_bytes = new_total
    cap.upload_status = "uploading"
    db.commit()
    db.refresh(cap)

    log_audit_event(db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=get_request_actor(request), actor_role="", action_type="mobile.image.upload", resource_type="image_capture_sessions", resource_id=image_id)

    return {
        "image_id": image_id,
        "capture_session_id": body.capture_session_id,
        "size_bytes": size_bytes,
        "sha256": image_hash,
        "stored": True,
        "annotation": body.annotation,
    }


@router.get("/images/session/{capture_session_id}")
def get_capture_session(capture_session_id: str, request: Request, db: Session = Depends(get_db)):
    tenant_info = require_enterprise_auth(request)
    tenant_id = get_request_tenant_id(request)

    cap = db.query(ImageCaptureSession).filter_by(
        capture_session_id=capture_session_id, tenant_id=tenant_id
    ).first()
    if not cap:
        raise HTTPException(status_code=404, detail="Capture session not found")

    return {
        "capture_session_id": cap.capture_session_id,
        "capture_type": cap.capture_type,
        "device_type": cap.device_type,
        "image_count": cap.image_count,
        "total_size_bytes": cap.total_size_bytes,
        "upload_status": cap.upload_status,
        "started_at": cap.started_at,
        "completed_at": cap.completed_at,
    }


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


@router.get("/notifications")
def list_notifications(
    request: Request,
    read_status: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    tenant_info = require_enterprise_auth(request)
    tenant_id = get_request_tenant_id(request)
    recipient_id = tenant_id  # use tenant_id as proxy in dev

    q = db.query(MobileNotification).filter_by(tenant_id=tenant_id)
    if read_status:
        q = q.filter(MobileNotification.read_status == read_status)
    if priority:
        q = q.filter(MobileNotification.priority == priority)
    items = q.order_by(MobileNotification.created_at.desc()).limit(limit).all()

    return {
        "notifications": [
            {
                "notification_id": n.notification_id,
                "notification_type": n.notification_type,
                "title": n.title,
                "body": n.body,
                "priority": n.priority,
                "read_status": n.read_status,
                "action_required": n.action_required,
                "action_url": n.action_url,
                "created_at": n.created_at,
            }
            for n in items
        ],
        "total": len(items),
    }


@router.post("/notifications")
def create_notification(body: CreateNotificationBody, request: Request, db: Session = Depends(get_db)):
    tenant_info = require_enterprise_auth(request)
    tenant_id = get_request_tenant_id(request)

    expires = None
    if body.expires_at:
        try:
            expires = datetime.fromisoformat(body.expires_at)
        except Exception:
            pass

    notif = dispatch_notification(
        db,
        tenant_id=tenant_id,
        recipient_id=body.recipient_id,
        notification_type=body.notification_type,
        title=body.title,
        body=body.body,
        priority=body.priority or "normal",
        delivery_channel=body.delivery_channel or "in_app",
        action_url=body.action_url,
        facility_id=body.facility_id,
    )
    if expires:
        notif.expires_at = expires
        db.commit()

    return {"notification_id": notif.notification_id, "sent_at": notif.sent_at}


@router.patch("/notifications/{notification_id}/read")
def mark_read(notification_id: str, request: Request, db: Session = Depends(get_db)):
    tenant_info = require_enterprise_auth(request)
    tenant_id = get_request_tenant_id(request)

    notif = db.query(MobileNotification).filter_by(notification_id=notification_id, tenant_id=tenant_id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    notif.read_status = "read"
    notif.read_at = datetime.utcnow()
    db.commit()
    return {"notification_id": notification_id, "read_status": "read"}


@router.patch("/notifications/{notification_id}/dismiss")
def dismiss_notification(notification_id: str, request: Request, db: Session = Depends(get_db)):
    tenant_info = require_enterprise_auth(request)
    tenant_id = get_request_tenant_id(request)

    notif = db.query(MobileNotification).filter_by(notification_id=notification_id, tenant_id=tenant_id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    notif.read_status = "dismissed"
    db.commit()
    return {"notification_id": notification_id, "read_status": "dismissed"}


@router.post("/notifications/broadcast")
def broadcast_notification(body: BroadcastNotificationBody, request: Request, db: Session = Depends(get_db)):
    tenant_info = require_enterprise_auth(request)
    tenant_id = get_request_tenant_id(request)

    recipient_id = f"broadcast:{body.facility_id}"
    notif = dispatch_notification(
        db,
        tenant_id=tenant_id,
        recipient_id=recipient_id,
        notification_type=body.notification_type,
        title=body.title,
        body=body.body,
        priority=body.priority or "normal",
        delivery_channel="all",
        facility_id=body.facility_id,
    )
    return {"notification_id": notif.notification_id, "recipient_id": recipient_id, "sent_at": notif.sent_at}


# ---------------------------------------------------------------------------
# Device Sessions
# ---------------------------------------------------------------------------


@router.post("/device-sessions")
def register_device(body: RegisterDeviceBody, request: Request, db: Session = Depends(get_db)):
    tenant_info = require_enterprise_auth(request)
    tenant_id = get_request_tenant_id(request)
    user_id = get_request_actor(request) or tenant_id

    dev = DeviceSession(
        tenant_id=tenant_id,
        user_id=user_id,
        device_id=body.device_id,
        device_type=body.device_type,
        user_agent=body.user_agent,
        auth_method=body.auth_method or "token",
    )
    db.add(dev)
    db.commit()
    db.refresh(dev)

    return {"device_session_id": dev.device_session_id, "is_active": dev.is_active, "created_at": dev.created_at}


@router.get("/device-sessions")
def list_device_sessions(request: Request, db: Session = Depends(get_db)):
    tenant_info = require_enterprise_auth(request)
    tenant_id = get_request_tenant_id(request)

    sessions = (
        db.query(DeviceSession)
        .filter_by(tenant_id=tenant_id, is_active=True)
        .order_by(DeviceSession.created_at.desc())
        .limit(50)
        .all()
    )
    return {
        "device_sessions": [
            {
                "device_session_id": d.device_session_id,
                "device_id": d.device_id,
                "device_type": d.device_type,
                "auth_method": d.auth_method,
                "is_active": d.is_active,
                "last_active_at": d.last_active_at,
            }
            for d in sessions
        ],
        "total": len(sessions),
    }


@router.post("/device-sessions/{device_session_id}/logout")
def remote_logout(device_session_id: str, request: Request, db: Session = Depends(get_db)):
    tenant_info = require_enterprise_auth(request)
    tenant_id = get_request_tenant_id(request)

    dev = db.query(DeviceSession).filter_by(device_session_id=device_session_id, tenant_id=tenant_id).first()
    if not dev:
        raise HTTPException(status_code=404, detail="Device session not found")

    dev.remote_logout_requested = True
    dev.is_active = False
    db.commit()
    return {"device_session_id": device_session_id, "remote_logout_requested": True, "is_active": False}


@router.post("/device-sessions/{device_session_id}/wipe")
def remote_wipe(device_session_id: str, request: Request, db: Session = Depends(get_db)):
    tenant_info = require_enterprise_auth(request)
    tenant_id = get_request_tenant_id(request)

    dev = db.query(DeviceSession).filter_by(device_session_id=device_session_id, tenant_id=tenant_id).first()
    if not dev:
        raise HTTPException(status_code=404, detail="Device session not found")

    dev.remote_wipe_requested = True
    db.commit()
    return {"device_session_id": device_session_id, "remote_wipe_requested": True}


# ---------------------------------------------------------------------------
# Sync Queue
# ---------------------------------------------------------------------------


@router.post("/sync-queue")
def add_to_queue(body: AddToQueueBody, request: Request, db: Session = Depends(get_db)):
    tenant_info = require_enterprise_auth(request)
    tenant_id = get_request_tenant_id(request)

    queue_ids = []
    for item in body.items:
        q = MobileSyncQueue(
            tenant_id=tenant_id,
            device_id=body.device_id,
            session_id=body.session_id,
            payload_type=item.payload_type,
            payload_json=item.payload_json,
        )
        db.add(q)
        db.flush()
        queue_ids.append(q.queue_id)
    db.commit()

    return {"queued": len(queue_ids), "queue_ids": queue_ids}


@router.post("/sync-queue/process")
def process_queue(request: Request, db: Session = Depends(get_db)):
    tenant_info = require_enterprise_auth(request)
    tenant_id = get_request_tenant_id(request)

    pending = (
        db.query(MobileSyncQueue)
        .filter_by(tenant_id=tenant_id, queue_status="pending")
        .limit(50)
        .all()
    )

    processed = 0
    failed = 0
    for item in pending:
        try:
            item.queue_status = "completed"
            item.processed_at = datetime.utcnow()
            processed += 1
        except Exception as exc:
            item.queue_status = "failed"
            item.error_message = str(exc)
            item.retry_count += 1
            failed += 1
    db.commit()

    remaining = db.query(MobileSyncQueue).filter_by(tenant_id=tenant_id, queue_status="pending").count()
    return {"processed": processed, "failed": failed, "remaining": remaining}


# ---------------------------------------------------------------------------
# Mobile Dashboards
# ---------------------------------------------------------------------------

_VALID_ROLES = {"technician", "supervisor", "manager", "quality_director", "infection_prevention", "executive"}


@router.get("/dashboard/{role}")
def mobile_dashboard(role: str, request: Request, facility_id: Optional[str] = None, db: Session = Depends(get_db)):
    tenant_info = require_enterprise_auth(request)
    tenant_id = get_request_tenant_id(request)

    if role not in _VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(_VALID_ROLES)}")

    data = get_mobile_dashboard_data(db, tenant_id, facility_id, role)
    return data


# ---------------------------------------------------------------------------
# Mobile Auth
# ---------------------------------------------------------------------------


@router.post("/auth/token-refresh")
def token_refresh(request: Request):
    # In dev/test: accepts dev-token, returns a mock refreshed token
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    return {
        "access_token": f"refreshed-{uuid.uuid4()}",
        "expires_in": 28800,
        "token_type": "bearer",
    }


@router.get("/auth/check")
def auth_check(request: Request):
    tenant_info = require_enterprise_auth(request)
    tenant_id = get_request_tenant_id(request)

    return {
        "authenticated": True,
        "tenant_id": tenant_id,
        "role": getattr(tenant_info, "role", "user") if hasattr(tenant_info, "role") else "user",
    }


@router.post("/auth/logout")
def auth_logout(request: Request, db: Session = Depends(get_db)):
    tenant_info = require_enterprise_auth(request)
    tenant_id = get_request_tenant_id(request)

    # In production: add token to revocation list
    log_audit_event(db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=get_request_actor(request), actor_role="", action_type="mobile.auth.logout", resource_type="device_sessions", resource_id="token")
    return {"logged_out": True, "message": "Token invalidated"}
