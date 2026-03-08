from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import time

from app.core.settings import settings
from app.routes.system import router as system_router
from app.routes.inspect import router as inspect_router
from app.routes.history import router as history_router
from app.routes.reports import router as reports_router
from app.routes.inspections import router as inspections_router
from app.db import Base, engine

app = FastAPI(title="LumenAI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def wait_for_db(max_attempts: int = 30, sleep_seconds: int = 2) -> None:
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"Database ready on attempt {attempt}")
            return
        except Exception as exc:
            last_error = exc
            print(f"Database not ready (attempt {attempt}/{max_attempts}): {exc}")
            time.sleep(sleep_seconds)
    raise RuntimeError(f"Database did not become ready: {last_error}")


@app.on_event("startup")
async def _startup() -> None:
    wait_for_db()
    Base.metadata.create_all(bind=engine)


app.include_router(system_router, prefix=settings.API_PREFIX)
app.include_router(inspect_router, prefix=settings.API_PREFIX)
app.include_router(history_router, prefix=settings.API_PREFIX)
app.include_router(reports_router, prefix=settings.API_PREFIX)
app.include_router(inspections_router, prefix=settings.API_PREFIX)
