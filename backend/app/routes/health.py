import os

from fastapi import APIRouter

router = APIRouter()


def _deployed_commit() -> str:
    """The git commit this process is running, for deployment verification.
    Render sets RENDER_GIT_COMMIT automatically; GIT_COMMIT/SOURCE_COMMIT/
    BUILD_MAIN_SHA are honored as fallbacks. 'unknown' when none is set."""
    return (
        os.getenv("RENDER_GIT_COMMIT")
        or os.getenv("GIT_COMMIT")
        or os.getenv("SOURCE_COMMIT")
        or os.getenv("BUILD_MAIN_SHA")
        or "unknown"
    )


@router.get("/api/health")
async def health():
    # git_commit lets an operator confirm which commit production is actually
    # running (e.g. that a merge reached the backend) without dashboard access.
    return {"status": "ok", "git_commit": _deployed_commit()}
