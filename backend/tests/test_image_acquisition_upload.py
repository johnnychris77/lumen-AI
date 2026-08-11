"""Image Acquisition Everywhere — governance on the shared upload path.

The "Image Acquisition Everywhere" sprint makes borescope *live capture* an
embedded image source alongside file upload. Both sources hand their frames to
the SAME governed endpoint the file-upload path already used
(``POST /api/inspections/upload-images``), so there is no second, weaker upload
path. These tests pin that invariant: authorization, the read-only viewer rule,
content-type/size validation, and tenant-scoped audit all still apply to a
borescope-captured frame, and the new ``image_source`` provenance field is
recorded without changing any of that behavior.
"""
import io

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

AUTH_ADMIN = {"Authorization": "Bearer dev-token"}          # admin
AUTH_OPERATOR = {"Authorization": "Bearer operator-token"}  # operator
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}      # viewer

VIEWER_MSG = "Viewer access is read-only"
_MAX_IMAGE_BYTES = 10 * 1024 * 1024


def _jpeg(name="borescope-capture-frame.jpg"):
    """A borescope-captured frame is a JPEG blob, exactly like BorescopeCapturePanel mints."""
    return {"images": (name, io.BytesIO(b"\xff\xd8\xff\xe0" + b"0" * 128), "image/jpeg")}


class TestAuthorizationPreserved:
    def test_unauthenticated_rejected(self):
        r = client.post(
            "/api/inspections/upload-images?image_source=borescope_capture",
            files=_jpeg(),
        )
        assert r.status_code in (401, 403), r.text

    def test_viewer_cannot_capture_or_upload(self):
        # A viewer must not be able to attach a borescope frame either.
        r = client.post(
            "/api/inspections/upload-images?image_source=borescope_capture",
            files=_jpeg(),
            headers=AUTH_VIEWER,
        )
        assert r.status_code == 403
        assert VIEWER_MSG in r.json()["detail"]

    def test_operator_can_attach_borescope_frame(self):
        r = client.post(
            "/api/inspections/upload-images?image_source=borescope_capture",
            files=_jpeg(),
            headers=AUTH_OPERATOR,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["uploaded"] == 1
        # SHA-256 hashing / evidence integrity is unchanged.
        assert len(body["images"][0]["sha256"]) == 64


class TestProvenanceRecorded:
    def test_borescope_source_echoed_per_image(self):
        r = client.post(
            "/api/inspections/upload-images?image_source=borescope_capture",
            files=_jpeg(),
            headers=AUTH_OPERATOR,
        )
        assert r.status_code == 200, r.text
        assert r.json()["images"][0]["image_source"] == "borescope_capture"

    def test_file_upload_source_echoed(self):
        r = client.post(
            "/api/inspections/upload-images?image_source=file_upload",
            files=_jpeg("existing-photo.jpg"),
            headers=AUTH_OPERATOR,
        )
        assert r.status_code == 200, r.text
        assert r.json()["images"][0]["image_source"] == "file_upload"

    def test_unknown_source_is_ignored_not_stored(self):
        # Provenance is a fixed whitelist — a spoofed/garbage value must not be
        # persisted as if it were a real source.
        r = client.post(
            "/api/inspections/upload-images?image_source=totally-made-up",
            files=_jpeg(),
            headers=AUTH_OPERATOR,
        )
        assert r.status_code == 200, r.text
        assert "image_source" not in r.json()["images"][0]

    def test_source_omitted_still_works(self):
        # Backward-compatible: callers that never send image_source are unaffected.
        r = client.post(
            "/api/inspections/upload-images",
            files=_jpeg("plain.jpg"),
            headers=AUTH_OPERATOR,
        )
        assert r.status_code == 200, r.text
        assert "image_source" not in r.json()["images"][0]


class TestValidationPreserved:
    def test_unsupported_content_type_rejected(self):
        r = client.post(
            "/api/inspections/upload-images?image_source=borescope_capture",
            files={"images": ("frame.gif", io.BytesIO(b"GIF89a" + b"0" * 32), "image/gif")},
            headers=AUTH_OPERATOR,
        )
        assert r.status_code == 422, r.text

    def test_empty_file_rejected(self):
        r = client.post(
            "/api/inspections/upload-images?image_source=borescope_capture",
            files={"images": ("frame.jpg", io.BytesIO(b""), "image/jpeg")},
            headers=AUTH_OPERATOR,
        )
        assert r.status_code == 422, r.text

    def test_oversized_file_rejected(self):
        big = io.BytesIO(b"\xff\xd8\xff\xe0" + b"0" * (_MAX_IMAGE_BYTES + 1))
        r = client.post(
            "/api/inspections/upload-images?image_source=borescope_capture",
            files={"images": ("frame.jpg", big, "image/jpeg")},
            headers=AUTH_OPERATOR,
        )
        assert r.status_code == 413, r.text


class TestTenantScoping:
    def test_response_tenant_is_server_derived(self):
        # Tenant comes from the request context on the server, and is stamped
        # onto every image record — the client never gets to place a frame under
        # an arbitrary tenant via the request body.
        r = client.post(
            "/api/inspections/upload-images?image_source=borescope_capture",
            files=_jpeg(),
            headers={**AUTH_ADMIN, "X-Tenant-Id": "bonsecours"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["images"][0]["tenant_id"] == "bonsecours"
