import json
import sqlite3
from pathlib import Path

import pytest

from src.database import (
    get_connection,
    initialize_database,
)
from src.exceptions import (
    persist_exception_signals,
)


# =========================================================
# HELPERS
# =========================================================

def insert_test_transaction(
    conn: sqlite3.Connection,
    transaction_id: str,
    amount: float = 15000.00,
) -> None:
    """
    Insert one trusted transaction for exception tests.
    """

    conn.execute(
        """
        INSERT INTO transactions (
            transaction_id,
            date,
            description,
            vendor,
            amount,
            transaction_type,
            category,
            department,
            currency
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            transaction_id,
            "2026-08-19",
            "Test Transaction",
            "AWS",
            amount,
            "expense",
            "Technology",
            "Engineering",
            "SGD",
        ),
    )


def make_signal(
    transaction_id: str,
    signal_type: str = "HIGH_VALUE",
    severity: str = "HIGH",
) -> dict:
    """
    Create one valid FinPilot test signal.
    """

    return {
        "transaction_id": transaction_id,
        "signal_type": signal_type,
        "source": "RULE",
        "severity": severity,
        "score": None,
        "reason": "Test financial control signal.",
        "evidence": {
            "amount": 15000.00,
            "threshold": 10000.00,
            "currency": "SGD",
        },
    }


# =========================================================
# NO-SIGNAL BEHAVIOUR
# =========================================================

def test_no_signals_create_no_exceptions(
    tmp_path: Path,
):
    """
    No signal means no exception should be created.
    """

    test_db = tmp_path / "test_finpilot.db"

    initialize_database(test_db)

    result = persist_exception_signals(
        [],
        test_db,
    )

    assert result == {
        "exceptions_created": 0,
        "signals_created": 0,
    }

    with get_connection(test_db) as conn:

        exception_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM exceptions
            """
        ).fetchone()[0]

    assert exception_count == 0


# =========================================================
# BASIC PERSISTENCE
# =========================================================

def test_signal_creates_exception_and_signal(
    tmp_path: Path,
):
    """
    One valid signal should create:

    1 transaction
        ↓
    1 exception
        ↓
    1 exception signal
    """

    test_db = tmp_path / "test_finpilot.db"

    initialize_database(test_db)

    with get_connection(test_db) as conn:
        insert_test_transaction(
            conn,
            "T0001",
        )

    signal = make_signal(
        "T0001"
    )

    result = persist_exception_signals(
        [signal],
        test_db,
    )

    assert result == {
        "exceptions_created": 1,
        "signals_created": 1,
    }

    with get_connection(test_db) as conn:

        exception = conn.execute(
            """
            SELECT
                transaction_id,
                priority,
                status
            FROM exceptions
            """
        ).fetchone()

        stored_signal = conn.execute(
            """
            SELECT
                transaction_id,
                signal_type,
                source,
                severity
            FROM exception_signals
            """
        ).fetchone()

    assert exception == (
        "T0001",
        "HIGH",
        "OPEN",
    )

    assert stored_signal == (
        "T0001",
        "HIGH_VALUE",
        "RULE",
        "HIGH",
    )


# =========================================================
# ONE EXCEPTION, MANY SIGNALS
# =========================================================

def test_multiple_signals_share_one_exception(
    tmp_path: Path,
):
    """
    Multiple signals for the same transaction should
    belong to one exception.
    """

    test_db = tmp_path / "test_finpilot.db"

    initialize_database(test_db)

    with get_connection(test_db) as conn:
        insert_test_transaction(
            conn,
            "T0001",
        )

    signals = [
        make_signal(
            "T0001",
            signal_type="HIGH_VALUE",
            severity="HIGH",
        ),
        make_signal(
            "T0001",
            signal_type="DUPLICATE_CANDIDATE",
            severity="MEDIUM",
        ),
    ]

    result = persist_exception_signals(
        signals,
        test_db,
    )

    assert result == {
        "exceptions_created": 1,
        "signals_created": 2,
    }

    with get_connection(test_db) as conn:

        exception_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM exceptions
            """
        ).fetchone()[0]

        signal_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM exception_signals
            """
        ).fetchone()[0]

    assert exception_count == 1
    assert signal_count == 2


# =========================================================
# PRIORITY
# =========================================================

def test_exception_uses_highest_signal_severity(
    tmp_path: Path,
):
    """
    Exception priority should equal the highest
    supporting signal severity.
    """

    test_db = tmp_path / "test_finpilot.db"

    initialize_database(test_db)

    with get_connection(test_db) as conn:
        insert_test_transaction(
            conn,
            "T0001",
        )

    signals = [
        make_signal(
            "T0001",
            signal_type="CONTROL_A",
            severity="LOW",
        ),
        make_signal(
            "T0001",
            signal_type="CONTROL_B",
            severity="MEDIUM",
        ),
        make_signal(
            "T0001",
            signal_type="CONTROL_C",
            severity="HIGH",
        ),
    ]

    persist_exception_signals(
        signals,
        test_db,
    )

    with get_connection(test_db) as conn:

        priority = conn.execute(
            """
            SELECT priority
            FROM exceptions
            WHERE transaction_id = ?
            """,
            ("T0001",),
        ).fetchone()[0]

    assert priority == "HIGH"


# =========================================================
# MULTIPLE TRANSACTIONS
# =========================================================

def test_different_transactions_create_different_exceptions(
    tmp_path: Path,
):
    """
    Signals belonging to different transactions should
    create separate exceptions.
    """

    test_db = tmp_path / "test_finpilot.db"

    initialize_database(test_db)

    with get_connection(test_db) as conn:

        insert_test_transaction(
            conn,
            "T0001",
        )

        insert_test_transaction(
            conn,
            "T0002",
        )

    signals = [
        make_signal("T0001"),
        make_signal("T0002"),
    ]

    result = persist_exception_signals(
        signals,
        test_db,
    )

    assert result == {
        "exceptions_created": 2,
        "signals_created": 2,
    }

    with get_connection(test_db) as conn:

        exception_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM exceptions
            """
        ).fetchone()[0]

    assert exception_count == 2


# =========================================================
# IDEMPOTENCY
# =========================================================

def test_repeated_signal_does_not_duplicate_records(
    tmp_path: Path,
):
    """
    Running the same signal twice should not create
    duplicate exceptions or duplicate signals.
    """

    test_db = tmp_path / "test_finpilot.db"

    initialize_database(test_db)

    with get_connection(test_db) as conn:
        insert_test_transaction(
            conn,
            "T0001",
        )

    signal = make_signal(
        "T0001"
    )

    first_result = persist_exception_signals(
        [signal],
        test_db,
    )

    second_result = persist_exception_signals(
        [signal],
        test_db,
    )

    assert first_result == {
        "exceptions_created": 1,
        "signals_created": 1,
    }

    assert second_result == {
        "exceptions_created": 0,
        "signals_created": 0,
    }

    with get_connection(test_db) as conn:

        exception_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM exceptions
            """
        ).fetchone()[0]

        signal_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM exception_signals
            """
        ).fetchone()[0]

    assert exception_count == 1
    assert signal_count == 1


# =========================================================
# JSON EVIDENCE
# =========================================================

def test_signal_evidence_is_valid_json(
    tmp_path: Path,
):
    """
    Evidence should be stored as valid JSON text
    that can later be used by the review UI or AI layer.
    """

    test_db = tmp_path / "test_finpilot.db"

    initialize_database(test_db)

    with get_connection(test_db) as conn:
        insert_test_transaction(
            conn,
            "T0001",
        )

    signal = make_signal(
        "T0001"
    )

    persist_exception_signals(
        [signal],
        test_db,
    )

    with get_connection(test_db) as conn:

        evidence_text = conn.execute(
            """
            SELECT evidence
            FROM exception_signals
            """
        ).fetchone()[0]

    evidence = json.loads(
        evidence_text
    )

    assert evidence["amount"] == 15000.00
    assert evidence["threshold"] == 10000.00
    assert evidence["currency"] == "SGD"


# =========================================================
# FOREIGN KEY PROTECTION
# =========================================================

def test_signal_for_unknown_transaction_is_rejected(
    tmp_path: Path,
):
    """
    FinPilot should not create an exception for a
    transaction that does not exist in trusted data.
    """

    test_db = tmp_path / "test_finpilot.db"

    initialize_database(test_db)

    signal = make_signal(
        "T_DOES_NOT_EXIST"
    )

    with pytest.raises(
        sqlite3.IntegrityError
    ):
        persist_exception_signals(
            [signal],
            test_db,
        )
        