"""
SQLite database backup and restore.

Uses file-level copy (safe when no active writes). Callers should reset the
SQLAlchemy engine after restore.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from src.database import DEFAULT_DB_PATH, reset_engine
from src.exceptions import DatabaseError

BACKUP_DIR = DEFAULT_DB_PATH.parent / "backups"


@dataclass(frozen=True)
class BackupInfo:
    """Metadata for one backup file."""

    path: Path
    filename: str
    created_at: datetime
    size_bytes: int


def _ensure_dirs() -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def create_backup(
    *,
    db_path: Path | None = None,
    label: str | None = None,
) -> BackupInfo:
    """
    Copy the live database to data/backups/ with a timestamped name.

    Raises DatabaseError if the source database does not exist.
    """
    source = db_path or DEFAULT_DB_PATH
    if not source.exists():
        raise DatabaseError(f"Database not found: {source}")

    _ensure_dirs()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = f"_{label.strip().replace(' ', '_')}" if label else ""
    filename = f"tracker_backup_{stamp}{suffix}.db"
    destination = BACKUP_DIR / filename

    shutil.copy2(source, destination)
    stat = destination.stat()
    return BackupInfo(
        path=destination,
        filename=filename,
        created_at=datetime.fromtimestamp(stat.st_mtime),
        size_bytes=stat.st_size,
    )


def list_backups() -> list[BackupInfo]:
    """Return backups newest-first."""
    _ensure_dirs()
    files = sorted(BACKUP_DIR.glob("tracker_backup_*.db"), reverse=True)
    result: list[BackupInfo] = []
    for path in files:
        stat = path.stat()
        result.append(
            BackupInfo(
                path=path,
                filename=path.name,
                created_at=datetime.fromtimestamp(stat.st_mtime),
                size_bytes=stat.st_size,
            )
        )
    return result


def restore_backup(
    backup_path: Path,
    *,
    db_path: Path | None = None,
    create_safety_copy: bool = True,
) -> Path:
    """
    Replace the live database with a backup copy.

    Optionally snapshots the current DB before overwrite. Resets the SQLAlchemy engine.
    """
    target = db_path or DEFAULT_DB_PATH
    if not backup_path.exists():
        raise DatabaseError(f"Backup file not found: {backup_path}")

    _ensure_dirs()
    if create_safety_copy and target.exists():
        create_backup(db_path=target, label="pre_restore")

    shutil.copy2(backup_path, target)
    reset_engine()
    return target
