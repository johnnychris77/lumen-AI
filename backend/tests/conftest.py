import importlib

import pytest


def _load_database_objects():
    candidates = [
        "app.database",
        "app.db",
        "app.core.database",
        "app.core.db",
        "app.config.database",
    ]

    last_error = None

    for module_name in candidates:
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:
            last_error = exc
            continue

        base = getattr(module, "Base", None)
        engine = getattr(module, "engine", None)

        if base is not None and engine is not None:
            return base, engine

    raise RuntimeError(
        f"Could not locate SQLAlchemy Base and engine. Last error: {last_error}"
    )


@pytest.fixture(autouse=True)
def ensure_test_database_tables():
    """
    Ensure SQLAlchemy tables exist before each test.

    This intentionally does not import every app module because this repository
    contains a nested app/app package that can duplicate SQLAlchemy model
    declarations during test discovery.
    """
    base, engine = _load_database_objects()
    base.metadata.create_all(bind=engine)
    yield
