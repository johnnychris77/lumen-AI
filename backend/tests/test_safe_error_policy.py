from app.core.errors import safe_error_payload


def test_safe_error_payload_has_standard_shape():
    payload = safe_error_payload(status_code=403, request_id="req_test")

    assert payload == {
        "error": {
            "code": "ACCESS_DENIED",
            "message": "You do not have permission to access this resource.",
            "request_id": "req_test",
            "status_code": 403,
        }
    }


def test_safe_error_payload_does_not_expose_internal_details():
    payload = str(safe_error_payload(status_code=500, request_id="req_test")).lower()

    forbidden_terms = [
        "traceback",
        "sql",
        "database",
        "exception",
        "file",
        "secret",
        "token",
        "password",
    ]

    for term in forbidden_terms:
        assert term not in payload


def test_unknown_status_uses_internal_error_safely():
    payload = safe_error_payload(status_code=599, request_id="req_test")

    assert payload["error"]["code"] == "INTERNAL_ERROR"
    assert payload["error"]["request_id"] == "req_test"
    assert payload["error"]["status_code"] == 599
