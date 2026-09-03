from __future__ import annotations

import sqlite3
from pathlib import Path


def initialise_database(database_path: Path) -> None:
    """Create the audit table used to prove what the automation did."""
    database_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS automation_runs (
                run_id TEXT PRIMARY KEY,
                start_time TEXT NOT NULL,
                end_time TEXT,
                input_file TEXT NOT NULL,
                output_report TEXT,
                total_records INTEGER DEFAULT 0,
                valid_records INTEGER DEFAULT 0,
                exception_records INTEGER DEFAULT 0,
                rows_with_exceptions INTEGER DEFAULT 0,
                run_status TEXT NOT NULL,
                error_message TEXT
            )
            """
        )
        connection.commit()


def start_run(database_path: Path, run_id: str, start_time: str, input_file: str) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO automation_runs (
                run_id,
                start_time,
                input_file,
                run_status
            )
            VALUES (?, ?, ?, ?)
            """,
            (run_id, start_time, input_file, "Running"),
        )
        connection.commit()


def complete_run(
    database_path: Path,
    run_id: str,
    end_time: str,
    output_report: str,
    total_records: int,
    valid_records: int,
    exception_records: int,
    rows_with_exceptions: int,
) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            UPDATE automation_runs
            SET
                end_time = ?,
                output_report = ?,
                total_records = ?,
                valid_records = ?,
                exception_records = ?,
                rows_with_exceptions = ?,
                run_status = ?
            WHERE run_id = ?
            """,
            (
                end_time,
                output_report,
                total_records,
                valid_records,
                exception_records,
                rows_with_exceptions,
                "Completed",
                run_id,
            ),
        )
        connection.commit()


def fail_run(database_path: Path, run_id: str, end_time: str, error_message: str) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            UPDATE automation_runs
            SET
                end_time = ?,
                run_status = ?,
                error_message = ?
            WHERE run_id = ?
            """,
            (end_time, "Failed", error_message, run_id),
        )
        connection.commit()
