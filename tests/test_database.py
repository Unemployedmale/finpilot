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


def test_database_initialization(tmp_path: Path):
    """The database should create a transactions table."""

    test_db = tmp_path / "test_finpilot.db"

    initialize_database(test_db)

    with get_connection(test_db) as conn:
        result = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            AND name='transactions'
            """
        ).fetchone()

    assert result is not None
    assert result[0] == "transactions"


def test_valid_transactions_are_saved(tmp_path: Path):
    """Validated transactions should be persisted successfully."""

    test_db = tmp_path / "test_finpilot.db"

    df = pd.read_csv("data/sample_transactions.csv")
    valid_df, invalid_df = validate_transactions(df)

    initialize_database(test_db)
    inserted_rows = save_transactions(valid_df, test_db)

    assert len(invalid_df) == 0
    assert inserted_rows == 10

    with get_connection(test_db) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM transactions"
        ).fetchone()[0]

    assert count == 10


def test_duplicate_transaction_id_is_rejected(tmp_path: Path):
    """The database should reject transaction IDs that already exist."""

    test_db = tmp_path / "test_finpilot.db"

    df = pd.read_csv("data/sample_transactions.csv")
    valid_df, _ = validate_transactions(df)

    initialize_database(test_db)

    save_transactions(valid_df, test_db)

    with pytest.raises(pd.errors.DatabaseError):
        save_transactions(valid_df, test_db)


def test_database_rejects_negative_amount(tmp_path: Path):
    """Database constraints should reject negative transaction amounts."""

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
    """Database constraints should reject unsupported currencies."""

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
