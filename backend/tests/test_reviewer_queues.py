"""Project Canvas — Section 20: Assignment and Queues tests.

Drives an annotation through primary review -> secondary review ->
agreement/disagreement -> adjudication -> Ground Truth eligibility via the
real HTTP surface, asserting each step moves the item between queues (and
never fabricates data the underlying tables don't support).
"""
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.retained_image import RetainedImage

client = TestClient(app)

AUTH_OPERATOR = {"Authorization": "Bearer operator-token"}
AUTH_MGR = {"Authorization": "Bearer manager-token"}
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
TENANT = "default-tenant"


def _make_retained_image(sha_suffix: str) -> int:
    db = SessionLocal()
    try:
        row = RetainedImage(
            tenant_id=TENANT, deident_name="test", instrument_type="scissors",
            content_type="image/png", size_bytes=100, sha256="q" * 56 + sha_suffix,
            exif_stripped=True, source="test", consent_recorded=True, uploaded_by="tester",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id
    finally:
        db.close()


def _create_annotation(image_id: int) -> int:
    r = client.post(
        "/api/annotations",
        json={"retained_image_id": image_id, "primary_observation": "no_observable_abnormality"},
        headers=AUTH_OPERATOR,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_queue_transitions_through_agreement():
    image_id = _make_retained_image("aaa1")
    annotation_id = _create_annotation(image_id)

    before = client.get("/api/reviewer-queues", headers=AUTH_ADMIN).json()
    assert any(a["id"] == annotation_id for a in before["queues"]["primary_review_due"])

    p = client.post(
        f"/api/annotations/{annotation_id}/review/primary",
        json={"label": "no_observable_abnormality", "confidence": 0.9},
        headers=AUTH_MGR,
    )
    assert p.status_code == 201, p.text

    mid = client.get("/api/reviewer-queues", headers=AUTH_ADMIN).json()
    assert not any(a["id"] == annotation_id for a in mid["queues"]["primary_review_due"])
    assert any(a["id"] == annotation_id for a in mid["queues"]["secondary_review_due"])

    s = client.post(
        f"/api/annotations/{annotation_id}/review/secondary",
        json={"label": "no_observable_abnormality", "confidence": 0.85},
        headers=AUTH_ADMIN,
    )
    assert s.status_code == 201, s.text
    assert s.json()["agreement"] is True

    after = client.get("/api/reviewer-queues", headers=AUTH_ADMIN).json()
    assert not any(a["id"] == annotation_id for a in after["queues"]["secondary_review_due"])
    assert not any(a["id"] == annotation_id for a in after["queues"]["disagreement"])
    assert any(a["id"] == annotation_id for a in after["queues"]["ground_truth_eligible"])


def test_queue_transitions_through_disagreement_and_adjudication():
    image_id = _make_retained_image("aaa2")
    annotation_id = _create_annotation(image_id)

    client.post(
        f"/api/annotations/{annotation_id}/review/primary",
        json={"label": "no_observable_abnormality", "confidence": 0.9},
        headers=AUTH_MGR,
    )
    s = client.post(
        f"/api/annotations/{annotation_id}/review/secondary",
        json={"label": "probable_retained_debris", "confidence": 0.7},
        headers=AUTH_ADMIN,
    )
    assert s.json()["agreement"] is False

    mid = client.get("/api/reviewer-queues", headers=AUTH_ADMIN).json()
    assert any(a["id"] == annotation_id for a in mid["queues"]["disagreement"])
    assert any(a["id"] == annotation_id for a in mid["queues"]["adjudication_due"])
    assert not any(a["id"] == annotation_id for a in mid["queues"]["ground_truth_eligible"])

    adj = client.post(
        f"/api/annotations/{annotation_id}/review/adjudicate",
        json={"resolution": "probable_retained_debris", "reason": "Adjudicator confirmed debris on re-review."},
        headers=AUTH_ADMIN,
    )
    assert adj.status_code == 200, adj.text

    after = client.get("/api/reviewer-queues", headers=AUTH_ADMIN).json()
    assert not any(a["id"] == annotation_id for a in after["queues"]["disagreement"])
    assert not any(a["id"] == annotation_id for a in after["queues"]["adjudication_due"])
    assert any(a["id"] == annotation_id for a in after["queues"]["ground_truth_eligible"])


def test_reviewer_queue_counts_are_consistent_with_lists():
    r = client.get("/api/reviewer-queues", headers=AUTH_ADMIN)
    assert r.status_code == 200
    body = r.json()
    for name, items in body["queues"].items():
        assert body["counts"][name] == len(items)
