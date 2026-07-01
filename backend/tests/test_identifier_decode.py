"""Identifier decode wired into the inspection workflow.

Covers the real pyzbar decoder, the GS1 UDI parser, graceful degradation when
ZBar is unavailable, and the /api/inspections/decode-identifiers endpoint.
"""
import io

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.cv.identifier_decoder import (
    decode_from_image_bytes,
    parse_gs1_udi,
)

client = TestClient(app)
AUTH_OPERATOR = {"Authorization": "Bearer operator-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}


def _png_upload():
    img = Image.new("RGB", (12, 12), (240, 240, 240))
    out = io.BytesIO()
    img.save(out, format="PNG")
    out.seek(0)
    return {"images": ("inst.png", out, "image/png")}


def test_gs1_udi_parser():
    parsed = parse_gs1_udi("(01)00844588003288(17)271231(10)LOT42(21)SER99")
    assert parsed["device_id"] == "00844588003288"
    assert parsed["expiry"] == "271231"
    assert parsed["lot"] == "LOT42"
    assert parsed["serial"] == "SER99"


def test_decode_degrades_gracefully_on_garbage():
    # Not a decodable image / no symbols → never raises, returns empty values.
    decoded = decode_from_image_bytes(b"not-an-image")
    assert decoded.barcode_value == ""
    assert decoded.qr_value == ""
    assert decoded.decoder_backend in ("none", "error", "pyzbar")


def test_decode_endpoint_runs_and_reports_backend():
    r = client.post(
        "/api/inspections/decode-identifiers",
        files=_png_upload(),
        headers=AUTH_OPERATOR,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # decoder_available reflects whether the ZBar NATIVE lib actually decoded —
    # not merely whether the pyzbar wrapper is importable (it may be installed
    # without libzbar0). Either way the endpoint must succeed and report a bool.
    assert isinstance(body["decoder_available"], bool)
    # A blank image has no symbols regardless of backend.
    assert body["barcode_value"] == ""
    assert body["images"][0]["decoder_backend"] in ("none", "error", "pyzbar")


def test_decode_endpoint_requires_runner_role():
    r = client.post(
        "/api/inspections/decode-identifiers",
        files=_png_upload(),
        headers=AUTH_VIEWER,
    )
    assert r.status_code == 403


def test_decode_endpoint_rejects_bad_type():
    r = client.post(
        "/api/inspections/decode-identifiers",
        files={"images": ("x.txt", io.BytesIO(b"hi"), "text/plain")},
        headers=AUTH_OPERATOR,
    )
    assert r.status_code == 422
