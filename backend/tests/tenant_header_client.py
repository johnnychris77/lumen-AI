"""Test client for the tenant-scoped analytics routes (P472-03).

The suites that predate P472-03 (benchmarking, P6 vendor intelligence, P7
predictions, P8 regulatory) authenticate with the shared development token and
named their tenant only as a ``tenant_id`` query parameter or body field. Since
P472-03 that is not enough: the tenant a request acts in comes from the verified
auth context, and for the development token that context reads ``X-Tenant-Id``.
A ``tenant_id`` in the request is only a claim that must agree with it.

This wrapper performs the migration every real client has to make: it sends the
tenant the request already names in the ``X-Tenant-Id`` header as well. Nothing
else about a request changes, and no assertion in those suites was altered.

It applies only to the four remediated route groups, only when the test sent an
``Authorization`` header, and never overrides an ``X-Tenant-Id`` the test set
itself — so tests of missing authentication and of tenant mismatch are untouched.
"""
from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

TENANT_SCOPED_PREFIXES = (
    "/api/regulatory",
    "/api/predictions",
    "/api/enterprise/benchmarks",
    "/api/vendor-intelligence",
)


class TenantHeaderClient:
    def __init__(self, client, *, default_tenant: str | None = None):
        self._client = client
        # The tenant to state when a request names none (suites written against a
        # server-side default tenant must now say which tenant they mean).
        self._default_tenant = default_tenant

    def __getattr__(self, name):
        return getattr(self._client, name)

    def _named_tenant(self, url: str, kwargs: dict) -> str | None:
        params = kwargs.get("params")
        if isinstance(params, dict) and params.get("tenant_id"):
            return str(params["tenant_id"])
        query = parse_qs(urlsplit(url).query).get("tenant_id")
        if query and query[0]:
            return query[0]
        body = kwargs.get("json")
        if isinstance(body, dict) and body.get("tenant_id"):
            return str(body["tenant_id"])
        return self._default_tenant

    def request(self, method: str, url: str, **kwargs):
        headers = dict(kwargs.get("headers") or {})
        lowered = {key.lower() for key in headers}
        if (
            urlsplit(url).path.startswith(TENANT_SCOPED_PREFIXES)
            and "authorization" in lowered
            and "x-tenant-id" not in lowered
        ):
            tenant = self._named_tenant(url, kwargs)
            if tenant:
                headers["X-Tenant-Id"] = tenant
                kwargs["headers"] = headers
        return self._client.request(method, url, **kwargs)

    def get(self, url: str, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs):
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs):
        return self.request("PUT", url, **kwargs)

    def patch(self, url: str, **kwargs):
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs):
        return self.request("DELETE", url, **kwargs)
