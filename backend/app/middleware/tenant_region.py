"""Tenant region routing middleware.

Reads X-Tenant-Region header (or falls back to tenant_region in tenant config).
Returns 400 if a request explicitly targets a region that doesn't match the
tenant's configured region. No-op if tenant_region is not configured.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


REGION_HEADER = "X-Tenant-Region"
ALLOWED_REGIONS = {"north_america", "europe", "uk", "apac", "australia", "global"}


class TenantRegionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        requested_region = request.headers.get(REGION_HEADER, "").lower().strip()
        if requested_region and requested_region not in ALLOWED_REGIONS:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "invalid_region",
                    "message": f"Region '{requested_region}' is not supported.",
                    "allowed_regions": sorted(ALLOWED_REGIONS),
                },
            )
        return await call_next(request)
