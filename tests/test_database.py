from pathlib import Path
import sqlite3

import pandas as pd
import pytest

from src.database import (
    get_connection,
    initialize_database,
    save_transactions,
)
from src.validation import validate_transactions


# =========================================================
# HELPER FUNCTION
# =========================================================

def insert_test_transaction(
    conn: sqlite3.Connection,
    transaction_id: str = "T9999",
) -> None:
    """
    Insert one valid transaction directly into the test database.

    This helper keeps the exception tests shorter and easier to read.
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
            "Test Vendor",
            15000.00,
            "expense",
            "Technology",
            "Engineering",
            "SGD",
        ),
    )


# =========================================================
# DATABASE INITIALIZATION TESTS
# =========================================================

def test_database_initialization(tmp_path: Path):
    """
    The database should create all required FinPilot tables.
    """

    test_db = tmp_path / "test_finpilot.db"

    initialize_database(test_db)

    with get_connection(test_db) as conn:
        tables = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            ORDER BY name
            """
        ).fetchall()

    table_names = {table[0] for table in tables}

    assert "transactions" in table_names
    assert "exceptions" in table_names
    assert "exception_signals" in table_names


def test_foreign_keys_are_enabled(tmp_path: Path):
    """
    SQLite foreign-key enforcement should be enabled
    whenever FinPilot opens a database connection.
    """

    test_db = tmp_path / "test_finpilot.db"

    initialize_database(test_db)

    with get_connection(test_db) as conn:
        foreign_keys_enabled = conn.execute(
            "PRAGMA foreign_keys"
        ).fetchone()[0]

    assert foreign_keys_enabled == 1


# =========================================================
# TRANSACTION TESTS
# =========================================================

def test_valid_transactions_are_saved(tmp_path: Path):
    """
    Validated transactions should be persisted successfully.
    """

    test_db = tmp_path / "test_finpilot.db"

    df = pd.read_csv("data/sample_transactions.csv")

    valid_df, invalid_df = validate_transactions(df)

    initialize_database(test_db)

    inserted_rows = save_transactions(
        valid_df,
        test_db,
    )

    assert len(invalid_df) == 0
    assert inserted_rows == 10

    with get_connection(test_db) as conn:
        count = conn.execute(
            """
            SELECT COUNT(*)
            FROM transactions
            """
        ).fetchone()[0]

    assert count == 10


def test_duplicate_transaction_id_is_rejected(tmp_path: Path):
    """
    The database should reject transaction IDs
    that already exist.
    """

    test_db = tmp_path / "test_finpilot.db"

    df = pd.read_csv("data/sample_transactions.csv")

    valid_df, _ = validate_transactions(df)

    initialize_database(test_db)

    save_transactions(
        valid_df,
        test_db,
    )

    with pytest.raises(pd.errors.DatabaseError):
        save_transactions(
            valid_df,
            test_db,
        )


def test_database_rejects_negative_amount(tmp_path: Path):
    """
    Database constraints should reject negative
    transaction amounts.
    """

    test_db = tmp_path / "test_finpilot.db"

    initialize_database(test_db)

    with get_connection(test_db) as conn:

        with pytest.raises(sqlite3.IntegrityError):

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
                    "T9999",
                    "2026-07-01",
                    "Invalid Test Transaction",
                    "Test Vendor",
                    -500.00,
                    "expense",
                    "Technology",
                    "Engineering",
                    "SGD",
                ),
            )


def test_database_rejects_invalid_currency(tmp_path: Path):
    """
    Database constraints should reject unsupported currencies.
    """

    test_db = tmp_path / "test_finpilot.db"

    initialize_database(test_db)

    with get_connection(test_db) as conn:

        with pytest.raises(sqlite3.IntegrityError):

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
                    "T9998",
                    "2026-07-01",
                    "Invalid Currency Test",
                    "Test Vendor",
                    500.00,
                    "expense",
                    "Technology",
                    "Engineering",
                    "ABC",
                ),
            )


# =========================================================
# EXCEPTION TESTS
# =========================================================

def test_exception_requires_existing_transaction(tmp_path: Path):
    """
    An exception must reference a transaction
    that actually exists.
    """

    test_db = tmp_path / "test_finpilot.db"

    initialize_database(test_db)

    with get_connection(test_db) as conn:

        with pytest.raises(sqlite3.IntegrityError):

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
                    "E0001",
                    "T_DOES_NOT_EXIST",
                    "HIGH",
                ),
            )


def test_exception_rejects_invalid_priority(tmp_path: Path):
    """
    Exception priority must be LOW, MEDIUM or HIGH.
    """

    test_db = tmp_path / "test_finpilot.db"

    initialize_database(test_db)

    with get_connection(test_db) as conn:

        insert_test_transaction(
            conn,
            transaction_id="T0001",
        )

        with pytest.raises(sqlite3.IntegrityError):

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
                    "E0001",
                    "T0001",
                    "SUPER_HIGH",
                ),
            )


def test_exception_rejects_invalid_status(tmp_path: Path):
    """
    Exception status must use one of the allowed
    review-workflow values.
    """

    test_db = tmp_path / "test_finpilot.db"

    initialize_database(test_db)

    with get_connection(test_db) as conn:

        insert_test_transaction(
            conn,
            transaction_id="T0001",
        )

        with pytest.raises(sqlite3.IntegrityError):

            conn.execute(
                """
                INSERT INTO exceptions (
                    exception_id,
                    transaction_id,
                    priority,
                    status
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    "E0001",
                    "T0001",
                    "HIGH",
                    "RANDOM_STATUS",
                ),
            )


def test_exception_default_status_is_open(tmp_path: Path):
    """
    A newly created exception should default to OPEN.
    """

    test_db = tmp_path / "test_finpilot.db"

    initialize_database(test_db)

    with get_connection(test_db) as conn:

        insert_test_transaction(
            conn,
            transaction_id="T0001",
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
                "E0001",
                "T0001",
                "HIGH",
            ),
        )

        status = conn.execute(
            """
            SELECT status
            FROM exceptions
            WHERE exception_id = ?
            """,
            ("E0001",),
        ).fetchone()[0]

    assert status == "OPEN"


# =========================================================
# EXCEPTION SIGNAL TESTS
# =========================================================

def test_signal_requires_existing_exception(tmp_path: Path):
    """
    An exception signal must reference
    an exception that actually exists.
    """

    test_db = tmp_path / "test_finpilot.db"

    initialize_database(test_db)

    with get_connection(test_db) as conn:

        insert_test_transaction(
            conn,
            transaction_id="T0001",
        )

        with pytest.raises(sqlite3.IntegrityError):

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
                    "S0001",
                    "E_DOES_NOT_EXIST",
                    "T0001",
                    "HIGH_VALUE",
                    "RULE",
                    "HIGH",
                    None,
                    "Transaction exceeds threshold.",
                    '{"amount": 15000, "threshold": 10000}',
                ),
            )


def test_signal_rejects_invalid_source(tmp_path: Path):
    """
    A signal source must currently be RULE or ML.
    """

    test_db = tmp_path / "test_finpilot.db"

    initialize_database(test_db)

    with get_connection(test_db) as conn:

        insert_test_transaction(
            conn,
            transaction_id="T0001",
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
                "E0001",
                "T0001",
                "HIGH",
            ),
        )

        with pytest.raises(sqlite3.IntegrityError):

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
                    "S0001",
                    "E0001",
                    "T0001",
                    "HIGH_VALUE",
                    "RANDOM_SOURCE",
                    "HIGH",
                    None,
                    "Transaction exceeds threshold.",
                    '{"amount": 15000, "threshold": 10000}',
                ),
            )


# =========================================================
# FULL RELATIONSHIP TEST
# =========================================================

def test_valid_transaction_exception_signal_relationship(
    tmp_path: Path,
):
    """
    A valid transaction should be able to have
    an exception with a valid supporting signal.

    This verifies the complete Day 2 database relationship:

    transaction
        ↓
    exception
        ↓
    exception signal
    """

    test_db = tmp_path / "test_finpilot.db"

    initialize_database(test_db)

    with get_connection(test_db) as conn:

        # -------------------------------------------------
        # Create transaction
        # -------------------------------------------------

        insert_test_transaction(
            conn,
            transaction_id="T0001",
        )

        # -------------------------------------------------
        # Create exception
        # -------------------------------------------------

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
                "E0001",
                "T0001",
                "HIGH",
            ),
        )

        # -------------------------------------------------
        # Create exception signal
        # -------------------------------------------------

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
                "S0001",
                "E0001",
                "T0001",
                "HIGH_VALUE",
                "RULE",
                "HIGH",
                None,
                "Transaction exceeds configured high-value threshold.",
                '{"amount": 15000, "threshold": 10000, "currency": "SGD"}',
            ),
        )

        # -------------------------------------------------
        # Read relationship back from database
        # -------------------------------------------------

        result = conn.execute(
            """
            SELECT
                t.transaction_id,
                e.exception_id,
                e.priority,
                e.status,
                s.signal_id,
                s.signal_type,
                s.source,
                s.severity
            FROM transactions AS t

            JOIN exceptions AS e
                ON t.transaction_id = e.transaction_id

            JOIN exception_signals AS s
                ON e.exception_id = s.exception_id

            WHERE t.transaction_id = ?
            """,
            ("T0001",),
        ).fetchone()

    assert result is not None

    assert result[0] == "T0001"
    assert result[1] == "E0001"
    assert result[2] == "HIGH"
    assert result[3] == "OPEN"
    assert result[4] == "S0001"
    assert result[5] == "HIGH_VALUE"
    assert result[6] == "RULE"
    assert result[7] == "HIGH"