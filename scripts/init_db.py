"""
CLI: initialize SQLite schema and optionally load sample data.

Usage (from project root):
    python scripts/init_db.py
    python scripts/init_db.py --seed
    python scripts/init_db.py --reset --seed
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import DEFAULT_DB_PATH, init_db, seed_sample_data  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize tracker database.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate all tables (destructive).",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Load shrinkflation demo rows after init.",
    )
    args = parser.parse_args()

    init_db(drop_existing=args.reset)
    if args.seed:
        seed_sample_data()

    print(f"Database ready: {DEFAULT_DB_PATH}")


if __name__ == "__main__":
    main()
