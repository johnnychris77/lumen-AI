"""ML image labeling + dataset-export API.

Drives the routes end-to-end via the real auth/role surface, including the
opt-in retention gate, multi-label annotation, the two-reviewer rule for
critical classes, and gold-only dataset export.
"""
import io

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app

client = TestClient(app)

AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_MGR = {"Authorization": "Bearer manager-token"}
AUTH_OPERATOR = {"Authorization": "Bearer operator-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}


def _png_upload():
    img = Image.new("RGB", (8, 8), (10, 10, 10))
    out = io.BytesIO()
    img.save(out, format="PNG")
    out.seek(0)
    return {"images": ("inst.png", out, "image/png")}


def _upload(monkeypatch_env=True):
    return client.post(
        "/api/ml/images?instrument_type=forceps&consent=true",
        files=_png_upload(),
        headers=AUTH_OPERATOR,
    )


def test_retention_status_endpoint():
    r = client.get("/api/ml/retention/status", headers=AUTH_OPERATOR)
    assert r.status_code == 200
    assert "retention_enabled" in r.json()


def test_upload_blocked_when_retention_disabled(monkeypatch):
    monkeypatch.delenv("RETAIN_INSPECTION_IMAGES", raising=False)
    r = _upload()
    assert r.status_code == 409


def test_viewer_cannot_upload(monkeypatch):
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "true")
    r = client.post(
        "/api/ml/images?consent=true", files=_png_upload(), headers=AUTH_VIEWER
    )
    assert r.status_code == 403


def test_label_and_export_flow(monkeypatch):
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "true")
    up = _upload()
    assert up.status_code == 201, up.text
    image_id = up.json()["images"][0]["id"]
    assert up.json()["images"][0]["exif_stripped"] is True

    # Non-critical label -> can be adjudicated by one reviewer.
    lab = client.post(
        f"/api/ml/images/{image_id}/labels",
        json={"finding_type": "rust", "severity": "moderate", "region": [0.1, 0.1, 0.2, 0.2]},
        headers=AUTH_OPERATOR,
    )
    assert lab.status_code == 201, lab.text
    assert lab.json()["requires_second_reviewer"] is False
    label_id = lab.json()["id"]

    adj = client.post(
        f"/api/ml/images/{image_id}/labels/{label_id}/adjudicate", headers=AUTH_MGR
    )
    assert adj.status_code == 200
    assert adj.json()["is_gold"] is True

    exp = client.get("/api/ml/dataset/export?gold_only=true", headers=AUTH_MGR)
    assert exp.status_code == 200
    body = exp.json()
    assert body["class_counts"].get("rust", 0) >= 1
    assert any(rec["image_id"] == image_id for rec in body["records"])


def test_critical_class_requires_two_reviewers(monkeypatch):
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "true")
    image_id = _upload().json()["images"][0]["id"]

    # First reviewer labels blood (critical).
    l1 = client.post(
        f"/api/ml/images/{image_id}/labels",
        json={"finding_type": "blood", "severity": "visible"},
        headers=AUTH_OPERATOR,
    )
    assert l1.json()["requires_second_reviewer"] is True
    label_id = l1.json()["id"]

    # Adjudicating with only one reviewer is blocked.
    blocked = client.post(
        f"/api/ml/images/{image_id}/labels/{label_id}/adjudicate", headers=AUTH_MGR
    )
    assert blocked.status_code == 409

    # A second distinct reviewer labels the same class, then adjudication passes.
    client.post(
        f"/api/ml/images/{image_id}/labels",
        json={"finding_type": "blood", "severity": "visible"},
        headers=AUTH_ADMIN,
    )
    ok = client.post(
        f"/api/ml/images/{image_id}/labels/{label_id}/adjudicate", headers=AUTH_MGR
    )
    assert ok.status_code == 200


def test_unknown_finding_type_rejected(monkeypatch):
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "true")
    image_id = _upload().json()["images"][0]["id"]
    r = client.post(
        f"/api/ml/images/{image_id}/labels",
        json={"finding_type": "sparkles"},
        headers=AUTH_OPERATOR,
    )
    assert r.status_code == 422
