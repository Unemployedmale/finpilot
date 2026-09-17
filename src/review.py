from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.database import DB_PATH, get_connection


VALID_EXCEPTION_STATUSES = {
    "OPEN",
    "CLEARED",
    "CONFIRMED_ISSUE",
    "NEEDS_INFO",
}


def get_exception_queue(
    db_path: Path = DB_PATH,
) -> pd.DataFrame:
    """
    Return FinPilot exceptions with transaction context
    and aggregated signal information.
    """

    query = """
        SELECT
            e.exception_id,
            e.transaction_id,
            e.priority,
            e.status,
            e.created_at,
            e.updated_at,

            t.date,
            t.vendor,
            t.description,
            t.amount,
            t.currency,
            t.transaction_type,
            t.category,
            t.department,

            COUNT(s.signal_id) AS signal_count,
            GROUP_CONCAT(
                DISTINCT s.signal_type
            ) AS signal_types

        FROM exceptions AS e

        JOIN transactions AS t
            ON e.transaction_id =
               t.transaction_id

        LEFT JOIN exception_signals AS s
            ON e.exception_id =
               s.exception_id

        GROUP BY
            e.exception_id,
            e.transaction_id,
            e.priority,
            e.status,
            e.created_at,
            e.updated_at,
            t.date,
            t.vendor,
            t.description,
            t.amount,
            t.currency,
            t.transaction_type,
            t.category,
            t.department

        ORDER BY
            CASE e.priority
                WHEN 'HIGH' THEN 1
                WHEN 'MEDIUM' THEN 2
                WHEN 'LOW' THEN 3
                ELSE 4
            END,
            e.created_at DESC
    """

    with get_connection(db_path) as conn:
        return pd.read_sql_query(
            query,
            conn,
        )


def get_exception_signals(
    exception_id: str,
    db_path: Path = DB_PATH,
) -> list[dict[str, Any]]:
    """
    Return all supporting signals for one exception.
    """

    query = """
        SELECT
            signal_id,
            transaction_id,
            signal_type,
            source,
            severity,
            score,
            reason,
            evidence,
            created_at

        FROM exception_signals

        WHERE exception_id = ?

        ORDER BY
            CASE severity
                WHEN 'HIGH' THEN 1
                WHEN 'MEDIUM' THEN 2
                WHEN 'LOW' THEN 3
                ELSE 4
            END,
            created_at
    """

    with get_connection(db_path) as conn:

        rows = conn.execute(
            query,
            (exception_id,),
        ).fetchall()

        columns = [
            "signal_id",
            "transaction_id",
            "signal_type",
            "source",
            "severity",
            "score",
            "reason",
            "evidence",
            "created_at",
        ]

    signals = []

    for row in rows:

        signal = dict(
            zip(
                columns,
                row,
            )
        )

        try:
            signal["evidence"] = json.loads(
                signal["evidence"]
            )

        except (
            json.JSONDecodeError,
            TypeError,
        ):
            pass

        signals.append(signal)

    return signals


def update_exception_status(
    exception_id: str,
    new_status: str,
    db_path: Path = DB_PATH,
) -> None:
    """
    Update the human-review status of an exception.
    """

    if new_status not in VALID_EXCEPTION_STATUSES:
        raise ValueError(
            f"Invalid exception status: {new_status}"
        )

    with get_connection(db_path) as conn:

        cursor = conn.execute(
            """
            UPDATE exceptions

            SET
                status = ?,
                updated_at = CURRENT_TIMESTAMP

            WHERE exception_id = ?
            """,
            (
                new_status,
                exception_id,
            ),
        )

        if cursor.rowcount == 0:
            raise ValueError(
                f"Unknown exception: {exception_id}"
            )


def get_dashboard_metrics(
    db_path: Path = DB_PATH,
) -> dict[str, int]:
    """
    Return headline metrics for the FinPilot dashboard.
    """

    with get_connection(db_path) as conn:

        transactions = conn.execute(
            """
            SELECT COUNT(*)
            FROM transactions
            """
        ).fetchone()[0]

        exceptions = conn.execute(
            """
            SELECT COUNT(*)
            FROM exceptions
            """
        ).fetchone()[0]

        open_exceptions = conn.execute(
            """
            SELECT COUNT(*)
            FROM exceptions
            WHERE status = 'OPEN'
            """
        ).fetchone()[0]

        high_priority = conn.execute(
            """
            SELECT COUNT(*)
            FROM exceptions
            WHERE priority = 'HIGH'
            """
        ).fetchone()[0]

    return {
        "transactions": transactions,
        "exceptions": exceptions,
        "open_exceptions": open_exceptions,
        "high_priority": high_priority,
    }


def clear_review_database(
    db_path: Path = DB_PATH,
) -> None:
    """
    Clear FinPilot development/demo records while
    preserving the database schema.
    """

    with get_connection(db_path) as conn:

        conn.execute(
            """
            DELETE FROM exception_signals
            """
        )

        conn.execute(
            """
            DELETE FROM exceptions
            """
        )

        conn.execute(
            """
            DELETE FROM transactions
            """
        )