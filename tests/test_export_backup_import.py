"""Tests for CSV export, backup/restore, and CSV import."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from src.backup.database_backup import create_backup, list_backups, restore_backup
from src.database import DEFAULT_DB_PATH, get_session, init_db, reset_engine
from src.entry_service import PriceEntryInput, save_price_entry
from src.export.csv_export import export_records_csv, export_records_csv_bytes, records_dataframe_for_export
from src.import_data.csv_import import import_records_from_csv


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "tools.db"
    reset_engine()
    init_db(path)
    save_price_entry(
        PriceEntryInput(
            item_name="Eggs",
            store_name="Shop",
            category_name="Dairy",
            price_total=8,
            date_recorded=date(2026, 5, 1),
        ),
        db_path=path,
    )
    yield path
    reset_engine()


def test_csv_export_bytes(db_path: Path) -> None:
    raw = export_records_csv_bytes(db_path=db_path)
    assert b"item_name" in raw
    assert b"Eggs" in raw


def test_csv_export_file(db_path: Path, tmp_path: Path) -> None:
    out = tmp_path / "export.csv"
    export_records_csv(out, db_path=db_path)
    df = pd.read_csv(out)
    assert len(df) == 1


def test_backup_and_restore(db_path: Path, tmp_path: Path) -> None:
    # Point backup module at tmp db by patching - backup uses DEFAULT_DB_PATH
    # Use copy approach: backup from db_path manually
    import shutil
    from src.backup import database_backup as bb

    original = bb.DEFAULT_DB_PATH
    bb.DEFAULT_DB_PATH = db_path
    bb.BACKUP_DIR = tmp_path / "backups"
    try:
        info = create_backup(db_path=db_path)
        assert info.path.exists()

        save_price_entry(
            PriceEntryInput(
                item_name="Bread",
                store_name="Shop",
                category_name="Bakery",
                price_total=5,
                date_recorded=date(2026, 5, 2),
            ),
            db_path=db_path,
        )
        assert len(records_dataframe_for_export(db_path=db_path)) == 2

        restore_backup(info.path, db_path=db_path, create_safety_copy=False)
        assert len(records_dataframe_for_export(db_path=db_path)) == 1
    finally:
        bb.DEFAULT_DB_PATH = original


def test_csv_import(db_path: Path) -> None:
    csv_content = (
        "item_name,store_name,category_name,price_total,date_recorded,quantity,unit_type\n"
        "Butter,Shop,Dairy,15.5,2026-05-10,1,unit\n"
    ).encode("utf-8")
    result = import_records_from_csv(csv_content, db_path=db_path, skip_duplicates=True)
    assert result.rows_imported == 1
    df = records_dataframe_for_export(db_path=db_path)
    assert "Butter" in df["item_name"].values
