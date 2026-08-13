"""A backend 500 must still carry CORS headers.

Regression: FastAPI/Starlette's ServerErrorMiddleware is the outermost layer,
outside the app's CORSMiddleware. An unhandled exception therefore produced a
500 with NO `Access-Control-Allow-Origin`, which the browser reported as a bare
"Failed to fetch" on credentialed cross-origin calls (notably the heavy
`POST /api/inspections` image-upload + AI-analysis path) — hiding the real
status and detail. `CorsSafeErrorMiddleware` catches the exception inside CORS
so the 500 response flows back out through CORSMiddleware and gets the headers.
"""
from fastapi.testclient import TestClient

from app.main import app

FRONTEND = "https://lumen-ai-1.onrender.com"

# A route that always raises, registered once on the real app so the test
# exercises the real middleware stack. The path is unique so it can't collide.
_BOOM_PATH = "/api/__test_cors_safe_boom__"


def _raise_boom():
    raise RuntimeError("intentional test failure")


app.add_api_route(_BOOM_PATH, _raise_boom, methods=["GET"], include_in_schema=False)

# raise_server_exceptions=False so the TestClient returns the 500 response
# (as a browser would receive it) instead of re-raising the exception.
client = TestClient(app, raise_server_exceptions=False)


def test_unhandled_500_still_has_cors_headers_for_frontend_origin():
    r = client.get(_BOOM_PATH, headers={"Origin": FRONTEND})
    assert r.status_code == 500
    # The critical assertion: without this header the browser reports the 500 as
    # "Failed to fetch" and the SPA can never show the real error.
    assert r.headers.get("access-control-allow-origin") == FRONTEND
    # And the body is JSON the frontend can parse and display.
    assert r.headers.get("content-type", "").startswith("application/json")
    body = r.json()
    assert "detail" in body


def test_unhandled_500_body_is_generic_not_leaky():
    """The 500 body must not leak the internal exception message/stack."""
    r = client.get(_BOOM_PATH, headers={"Origin": FRONTEND})
    body = r.json()
    assert "intentional test failure" not in str(body)
    assert "Traceback" not in str(body)
