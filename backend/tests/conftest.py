import importlib
from pathlib import Path

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


def _import_model_modules():
    """
    Import only real app model/service modules needed by compliance evidence tests.
    Avoid importing nested app/app modules because they redeclare existing tables.
    """
    backend_root = Path(__file__).resolve().parents[1]
    app_root = backend_root / "app"

    for file_path in app_root.rglob("*.py"):
        relative = file_path.relative_to(backend_root)

        # Avoid duplicate nested package that caused duplicate inspections table.
        if "app/app/" in relative.as_posix():
            continue

        text = file_path.read_text(errors="ignore")

        if (
            "__tablename__" not in text
            and "EnterpriseAudit" not in text
            and "audit_logs" not in text
        ):
            continue

        module_name = ".".join(relative.with_suffix("").parts)

        if module_name.endswith(".main"):
            continue

        try:
            importlib.import_module(module_name)
        except Exception:
            continue


@pytest.fixture(autouse=True)
def ensure_test_database_tables():
    base, engine = _load_database_objects()
    _import_model_modules()
    base.metadata.create_all(bind=engine)
    yield
