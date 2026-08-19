from __future__ import annotations

import json
import sqlite3
import uuid
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from src.database import DB_PATH, get_connection


# =========================================================
# CONSTANTS
# =========================================================

SEVERITY_RANK = {
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
}

VALID_SOURCES = {
    "RULE",
    "ML",
}


# =========================================================
# INTERNAL HELPERS
# =========================================================

def _generate_id(prefix: str) -> str:
    """
    Generate a unique identifier.

    Example:
        EXC_A81C93F10B23
        SIG_94D21B804311
    """

    unique_part = uuid.uuid4().hex[:12].upper()

    return f"{prefix}_{unique_part}"


def _validate_signal(
    signal: Mapping[str, Any],
) -> None:
    """
    Validate the minimum structure required for a
    FinPilot exception signal.

    This catches programming errors before invalid data
    reaches SQLite.
    """

    required_fields = {
        "transaction_id",
        "signal_type",
        "source",
        "severity",
        "score",
        "reason",
        "evidence",
    }

    missing_fields = required_fields - signal.keys()

    if missing_fields:
        raise ValueError(
            f"Signal is missing required fields: "
            f"{sorted(missing_fields)}"
        )

    transaction_id = str(
        signal["transaction_id"]
    ).strip()

    signal_type = str(
        signal["signal_type"]
    ).strip()

    source = str(
        signal["source"]
    ).strip()

    severity = str(
        signal["severity"]
    ).strip()

    reason = str(
        signal["reason"]
    ).strip()

    if not transaction_id:
        raise ValueError(
            "Signal transaction_id cannot be blank."
        )

    if not signal_type:
        raise ValueError(
            "Signal signal_type cannot be blank."
        )

    if source not in VALID_SOURCES:
        raise ValueError(
            f"Invalid signal source: {source}"
        )

    if severity not in SEVERITY_RANK:
        raise ValueError(
            f"Invalid signal severity: {severity}"
        )

    if not reason:
        raise ValueError(
            "Signal reason cannot be blank."
        )

    if not isinstance(
        signal["evidence"],
        Mapping,
    ):
        raise ValueError(
            "Signal evidence must be a dictionary-like object."
        )


def _highest_severity(
    signals: Sequence[Mapping[str, Any]],
) -> str:
    """
    Return the highest severity from a collection
    of signals.
    """

    return max(
        (
            str(signal["severity"])
            for signal in signals
        ),
        key=lambda severity: SEVERITY_RANK[severity],
    )


def _serialize_evidence(
    evidence: Mapping[str, Any],
) -> str:
    """
    Convert evidence into consistent JSON text
    for SQLite storage.

    sort_keys=True makes identical evidence produce
    identical stored JSON, which helps with duplicate
    detection.
    """

    return json.dumps(
        dict(evidence),
        sort_keys=True,
        default=str,
    )


def _get_open_exception(
    conn: sqlite3.Connection,
    transaction_id: str,
) -> tuple[str, str] | None:
    """
    Find an existing OPEN exception for a transaction.

    Returns:
        (exception_id, priority)

    or:
        None
    """

    result = conn.execute(
        """
        SELECT
            exception_id,
            priority
        FROM exceptions
        WHERE transaction_id = ?
          AND status = 'OPEN'
        ORDER BY created_at
        LIMIT 1
        """,
        (transaction_id,),
    ).fetchone()

    if result is None:
        return None

    return result[0], result[1]


def _signal_already_exists(
    conn: sqlite3.Connection,
    exception_id: str,
    signal: Mapping[str, Any],
    evidence_json: str,
) -> bool:
    """
    Check whether an identical signal has already
    been stored for the exception.

    This prevents repeated control runs from creating
    duplicate copies of the same signal.
    """

    score = signal["score"]

    result = conn.execute(
        """
        SELECT signal_id
        FROM exception_signals
        WHERE exception_id = ?
          AND transaction_id = ?
          AND signal_type = ?
          AND source = ?
          AND severity = ?
          AND reason = ?
          AND evidence = ?
          AND (
                score = ?
                OR (
                    score IS NULL
                    AND ? IS NULL
                )
              )
        LIMIT 1
        """,
        (
            exception_id,
            str(signal["transaction_id"]),
            str(signal["signal_type"]),
            str(signal["source"]),
            str(signal["severity"]),
            str(signal["reason"]),
            evidence_json,
            score,
            score,
        ),
    ).fetchone()

    return result is not None


# =========================================================
# MAIN PERSISTENCE FUNCTION
# =========================================================

def persist_exception_signals(
    signals: Sequence[Mapping[str, Any]],
    db_path: Path = DB_PATH,
) -> dict[str, int]:
    """
    Convert FinPilot signals into persisted exceptions
    and exception signals.

    Rules
    -----
    1. No signals -> no exception.
    2. Signals are grouped by transaction.
    3. One OPEN exception is reused per transaction.
    4. Exception priority is based on highest severity.
    5. Identical signals are not inserted twice.
    6. All relationships are protected by SQLite
       foreign keys.

    Returns
    -------
    dict[str, int]

    Example:

        {
            "exceptions_created": 2,
            "signals_created": 3
        }
    """

    if not signals:
        return {
            "exceptions_created": 0,
            "signals_created": 0,
        }

    # -----------------------------------------------------
    # Validate signals first
    # -----------------------------------------------------

    for signal in signals:
        _validate_signal(signal)

    # -----------------------------------------------------
    # Group signals by transaction
    # -----------------------------------------------------

    signals_by_transaction: dict[
        str,
        list[Mapping[str, Any]],
    ] = defaultdict(list)

    for signal in signals:

        transaction_id = str(
            signal["transaction_id"]
        )

        signals_by_transaction[
            transaction_id
        ].append(signal)

    exceptions_created = 0
    signals_created = 0

    # -----------------------------------------------------
    # Persist everything in one database transaction
    # -----------------------------------------------------

    with get_connection(db_path) as conn:

        for (
            transaction_id,
            transaction_signals,
        ) in signals_by_transaction.items():

            new_priority = _highest_severity(
                transaction_signals
            )

            existing_exception = (
                _get_open_exception(
                    conn,
                    transaction_id,
                )
            )

            # -------------------------------------------------
            # Reuse an OPEN exception if one already exists
            # -------------------------------------------------

            if existing_exception is not None:

                exception_id = (
                    existing_exception[0]
                )

                existing_priority = (
                    existing_exception[1]
                )

                # Never accidentally reduce the priority
                # of an existing open exception.
                final_priority = max(
                    [
                        existing_priority,
                        new_priority,
                    ],
                    key=lambda priority: (
                        SEVERITY_RANK[priority]
                    ),
                )

                if final_priority != existing_priority:

                    conn.execute(
                        """
                        UPDATE exceptions
                        SET
                            priority = ?,
                            updated_at =
                                CURRENT_TIMESTAMP
                        WHERE exception_id = ?
                        """,
                        (
                            final_priority,
                            exception_id,
                        ),
                    )

            # -------------------------------------------------
            # Otherwise create a new exception
            # -------------------------------------------------

            else:

                exception_id = _generate_id(
                    "EXC"
                )

                conn.execute(
                    """
                    INSERT INTO exceptions (
                        exception_id,
                        transaction_id,
                        priority
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        exception_id,
                        transaction_id,
                        new_priority,
                    ),
                )

                exceptions_created += 1

            # -------------------------------------------------
            # Persist supporting signals
            # -------------------------------------------------

            for signal in transaction_signals:

                evidence_json = (
                    _serialize_evidence(
                        signal["evidence"]
                    )
                )

                if _signal_already_exists(
                    conn,
                    exception_id,
                    signal,
                    evidence_json,
                ):
                    continue

                signal_id = _generate_id(
                    "SIG"
                )

                conn.execute(
                    """
                    INSERT INTO exception_signals (
                        signal_id,
                        exception_id,
                        transaction_id,
                        signal_type,
                        source,
                        severity,
                        score,
                        reason,
                        evidence
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        signal_id,
                        exception_id,
                        transaction_id,
                        str(
                            signal[
                                "signal_type"
                            ]
                        ),
                        str(signal["source"]),
                        str(signal["severity"]),
                        signal["score"],
                        str(signal["reason"]),
                        evidence_json,
                    ),
                )

                signals_created += 1

    return {
        "exceptions_created": (
            exceptions_created
        ),
        "signals_created": (
            signals_created
        ),
    }