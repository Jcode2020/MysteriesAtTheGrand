#!/usr/bin/env python3
"""Delete all rows from the local SQLite hotel database without dropping tables."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


DEFAULT_DATABASE_PATH = Path(__file__).resolve().parent / "hotel_db.sqlite3"


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the database wipe utility."""
    parser = argparse.ArgumentParser(
        description="Delete all rows from the SQLite hotel database while keeping the schema.",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE_PATH,
        help="Path to the SQLite database file. Defaults to db/hotel_db.sqlite3.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm that all table rows should be deleted.",
    )
    return parser.parse_args()


def _quote_identifier(identifier: str) -> str:
    """Quote a SQLite identifier so table names remain safe in SQL."""
    return '"' + identifier.replace('"', '""') + '"'


def _fetch_user_tables(connection: sqlite3.Connection) -> list[str]:
    """Return all non-internal SQLite tables in a stable order."""
    table_rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name ASC
        """
    ).fetchall()
    return [row[0] for row in table_rows]


def clear_database(database_path: Path) -> dict[str, int]:
    """Delete all rows from all user tables and reset autoincrement counters."""
    if not database_path.exists():
        raise FileNotFoundError(f"Database file not found: {database_path}")

    deleted_row_counts: dict[str, int] = {}

    with sqlite3.connect(database_path) as connection:
        table_names = _fetch_user_tables(connection)
        if not table_names:
            return deleted_row_counts

        deleted_row_counts = {
            table_name: connection.execute(
                f"SELECT COUNT(*) FROM {_quote_identifier(table_name)}"
            ).fetchone()[0]
            for table_name in table_names
        }

        # Disable foreign-key checks temporarily so self-referential history rows
        # can be deleted in one pass while the schema stays intact.
        connection.execute("PRAGMA foreign_keys = OFF;")
        try:
            for table_name in table_names:
                connection.execute(f"DELETE FROM {_quote_identifier(table_name)}")

            sqlite_sequence_exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'sqlite_sequence'"
            ).fetchone()
            if sqlite_sequence_exists is not None:
                placeholders = ", ".join("?" for _ in table_names)
                connection.execute(
                    f"DELETE FROM sqlite_sequence WHERE name IN ({placeholders})",
                    table_names,
                )

            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.execute("PRAGMA foreign_keys = ON;")

    return deleted_row_counts


def main() -> int:
    """Run the database wipe utility."""
    args = parse_args()
    database_path = args.database.expanduser().resolve()

    if not args.yes:
        print("Refusing to delete database rows without --yes.")
        print(f"Target database: {database_path}")
        return 1

    deleted_row_counts = clear_database(database_path)
    if not deleted_row_counts:
        print(f"No user tables found in {database_path}. Nothing changed.")
        return 0

    total_deleted_rows = sum(deleted_row_counts.values())
    print(f"Cleared {total_deleted_rows} rows from {database_path}.")
    for table_name, row_count in deleted_row_counts.items():
        print(f"- {table_name}: deleted {row_count} rows")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
