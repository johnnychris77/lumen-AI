"""ensure_columns back-fills columns missing from an existing table.

Reproduces the production failure: an old `inspections` table without the newer
columns caused inspection/history endpoints to 500 (seen in the browser as a
CORS error). After back-fill the columns exist and queries work.
"""
from sqlalchemy import create_engine, text

from app.db.column_migrator import ensure_columns
from app.models.inspection import Inspection


def test_ensure_columns_adds_missing(tmp_path):
    db_path = tmp_path / "old.db"
    engine = create_engine(f"sqlite:///{db_path}")

    # Simulate an OLD inspections table missing the newer columns.
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE inspections ("
            "id INTEGER PRIMARY KEY, file_name VARCHAR, tenant_id VARCHAR, "
            "instrument_type VARCHAR)"
        ))
        conn.execute(text(
            "INSERT INTO inspections (file_name, tenant_id, instrument_type) "
            "VALUES ('old.jpg', 't1', 'scissors')"
        ))

    added = ensure_columns(engine, Inspection)

    # Newer columns that were missing must now have been added.
    for col in ("has_image", "baseline_status", "baseline_source",
                "score_status", "supervisor_review_required", "image_sha256"):
        assert col in added, f"{col} should have been back-filled"

    # The previously-missing columns are now queryable (no 500).
    from sqlalchemy import inspect as sqla_inspect
    cols = {c["name"] for c in sqla_inspect(engine).get_columns("inspections")}
    assert {"has_image", "baseline_status", "score_status"} <= cols


def test_ensure_columns_idempotent(tmp_path):
    db_path = tmp_path / "idem.db"
    engine = create_engine(f"sqlite:///{db_path}")
    # Create the table fully from the model, then re-run — nothing to add.
    Inspection.__table__.create(engine)
    added = ensure_columns(engine, Inspection)
    assert added == []
