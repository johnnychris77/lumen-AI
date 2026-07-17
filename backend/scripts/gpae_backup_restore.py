"""Project Foundation (GPAE) — backup and restore tooling.

Backs up (and restores) the three persistence surfaces Foundation
Sections 11-12 name:

  1. the authoritative database (PostgreSQL via pg_dump/pg_restore, or a
     SQLite file via the sqlite3 backup API),
  2. governed object storage (the LUMENAI_LOCAL_STORAGE_DIR tree; for an
     S3 backend, use the provider's replication — documented in
     docs/foundation/BACKUP_RESTORE.md),
  3. registered model artifacts (the model_artifacts/ directory).

Every backup writes a MANIFEST.json with the SHA-256 of each archive so a
restore can verify integrity before touching anything. Timings are
printed so restore tests can record real RTO numbers.

Usage:
  python scripts/gpae_backup_restore.py backup  --out /path/to/backups
  python scripts/gpae_backup_restore.py restore --backup /path/to/backups/gpae-backup-<ts>
  python scripts/gpae_backup_restore.py verify  --backup /path/to/backups/gpae-backup-<ts>

DATABASE_URL selects the database. Restore to PostgreSQL requires the
target database to exist (it is dropped-and-recreated at the schema level
via pg_restore --clean --if-exists).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise SystemExit("DATABASE_URL is not set.")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def _storage_dir() -> Path:
    return Path(os.environ.get("LUMENAI_LOCAL_STORAGE_DIR", "./data/lumenai-storage"))


def _artifacts_dir() -> Path:
    return Path(os.environ.get("LUMENAI_MODEL_ARTIFACTS_DIR", "./model_artifacts"))


def _tar_dir(source: Path, target: Path) -> bool:
    if not source.exists():
        return False
    with tarfile.open(target, "w:gz") as tar:
        tar.add(source, arcname=source.name)
    return True


def _untar(archive: Path, into_parent: Path) -> None:
    with tarfile.open(archive, "r:gz") as tar:
        tar.extractall(into_parent, filter="data")


def backup(out_dir: Path) -> Path:
    started = time.perf_counter()
    url = _database_url()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = out_dir / f"gpae-backup-{stamp}"
    backup_dir.mkdir(parents=True, exist_ok=False)

    manifest: dict = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "database_kind": "",
        "components": {},
    }

    # 1. Database.
    db_started = time.perf_counter()
    if url.startswith("sqlite"):
        manifest["database_kind"] = "sqlite"
        db_path = Path(url.split("///", 1)[1])
        target = backup_dir / "database.sqlite3"
        src = sqlite3.connect(db_path)
        dst = sqlite3.connect(target)
        with dst:
            src.backup(dst)
        src.close()
        dst.close()
    elif url.startswith("postgresql"):
        manifest["database_kind"] = "postgresql"
        target = backup_dir / "database.pgdump"
        subprocess.run(
            ["pg_dump", "--format=custom", f"--dbname={url}", f"--file={target}"],
            check=True,
        )
    else:
        raise SystemExit(f"Unsupported DATABASE_URL scheme: {url.split(':', 1)[0]}")
    manifest["components"]["database"] = {
        "file": target.name,
        "sha256": _sha256_file(target),
        "seconds": round(time.perf_counter() - db_started, 3),
    }

    # 2. Object storage (local backend).
    st_started = time.perf_counter()
    storage_tar = backup_dir / "object-storage.tar.gz"
    if _tar_dir(_storage_dir(), storage_tar):
        manifest["components"]["object_storage"] = {
            "file": storage_tar.name,
            "sha256": _sha256_file(storage_tar),
            "source_dir": str(_storage_dir()),
            "seconds": round(time.perf_counter() - st_started, 3),
        }
    else:
        manifest["components"]["object_storage"] = {"file": None, "note": "source dir absent"}

    # 3. Model artifacts.
    ar_started = time.perf_counter()
    artifacts_tar = backup_dir / "model-artifacts.tar.gz"
    if _tar_dir(_artifacts_dir(), artifacts_tar):
        manifest["components"]["model_artifacts"] = {
            "file": artifacts_tar.name,
            "sha256": _sha256_file(artifacts_tar),
            "source_dir": str(_artifacts_dir()),
            "seconds": round(time.perf_counter() - ar_started, 3),
        }
    else:
        manifest["components"]["model_artifacts"] = {"file": None, "note": "source dir absent"}

    manifest["total_seconds"] = round(time.perf_counter() - started, 3)
    (backup_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps({"backup_dir": str(backup_dir), **manifest}, indent=2))
    return backup_dir


def verify(backup_dir: Path) -> dict:
    manifest = json.loads((backup_dir / "MANIFEST.json").read_text())
    results = {}
    ok = True
    for name, comp in manifest["components"].items():
        if not comp.get("file"):
            results[name] = "absent_at_backup_time"
            continue
        path = backup_dir / comp["file"]
        if not path.exists():
            results[name] = "MISSING"
            ok = False
            continue
        actual = _sha256_file(path)
        if actual == comp["sha256"]:
            results[name] = "sha256_verified"
        else:
            results[name] = f"SHA256_MISMATCH expected={comp['sha256']} actual={actual}"
            ok = False
    report = {"backup_dir": str(backup_dir), "verified": ok, "components": results}
    print(json.dumps(report, indent=2))
    if not ok:
        raise SystemExit("Backup verification FAILED — do not restore from this backup.")
    return report


def restore(backup_dir: Path) -> None:
    started = time.perf_counter()
    verify(backup_dir)
    manifest = json.loads((backup_dir / "MANIFEST.json").read_text())
    url = _database_url()

    # 1. Database.
    db_started = time.perf_counter()
    kind = manifest["database_kind"]
    if kind == "sqlite":
        if not url.startswith("sqlite"):
            raise SystemExit("Backup is sqlite but DATABASE_URL is not — refusing cross-engine restore.")
        db_path = Path(url.split("///", 1)[1])
        shutil.copyfile(backup_dir / "database.sqlite3", db_path)
    elif kind == "postgresql":
        if not url.startswith("postgresql"):
            raise SystemExit("Backup is postgresql but DATABASE_URL is not — refusing cross-engine restore.")
        subprocess.run(
            [
                "pg_restore",
                "--clean",
                "--if-exists",
                "--no-owner",
                f"--dbname={url}",
                str(backup_dir / "database.pgdump"),
            ],
            check=True,
        )
    db_seconds = round(time.perf_counter() - db_started, 3)

    # 2. Object storage.
    st_started = time.perf_counter()
    storage_tar = backup_dir / "object-storage.tar.gz"
    storage_seconds = None
    if storage_tar.exists():
        storage_dir = _storage_dir()
        if storage_dir.exists():
            shutil.rmtree(storage_dir)
        _untar(storage_tar, storage_dir.parent)
        storage_seconds = round(time.perf_counter() - st_started, 3)

    # 3. Model artifacts.
    ar_started = time.perf_counter()
    artifacts_tar = backup_dir / "model-artifacts.tar.gz"
    artifacts_seconds = None
    if artifacts_tar.exists():
        artifacts_dir = _artifacts_dir()
        if artifacts_dir.exists():
            shutil.rmtree(artifacts_dir)
        _untar(artifacts_tar, artifacts_dir.parent)
        artifacts_seconds = round(time.perf_counter() - ar_started, 3)

    print(
        json.dumps(
            {
                "restored_from": str(backup_dir),
                "database_seconds": db_seconds,
                "object_storage_seconds": storage_seconds,
                "model_artifacts_seconds": artifacts_seconds,
                "total_seconds": round(time.perf_counter() - started, 3),
            },
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p_backup = sub.add_parser("backup")
    p_backup.add_argument("--out", required=True, type=Path)
    p_restore = sub.add_parser("restore")
    p_restore.add_argument("--backup", required=True, type=Path)
    p_verify = sub.add_parser("verify")
    p_verify.add_argument("--backup", required=True, type=Path)
    args = parser.parse_args()

    if args.command == "backup":
        backup(args.out)
    elif args.command == "restore":
        restore(args.backup)
    elif args.command == "verify":
        verify(args.backup)


if __name__ == "__main__":
    sys.exit(main())
