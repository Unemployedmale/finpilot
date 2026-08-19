from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


DB_PATH = Path("finpilot.db")


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """
    Create and return a connection to the FinPilot SQLite database.
    """
    return sqlite3.connect(db_path)


def initialize_database(db_path: Path = DB_PATH) -> None:
    """
    Create the FinPilot database and transactions table if they do not exist.
    """
    with get_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id TEXT PRIMARY KEY,
                date TEXT NOT NULL,
                description TEXT NOT NULL,
                vendor TEXT NOT NULL,
                amount REAL NOT NULL CHECK (amount > 0),
                transaction_type TEXT NOT NULL
                    CHECK (transaction_type IN ('revenue', 'expense')),
                category TEXT NOT NULL,
                department TEXT NOT NULL,
                currency TEXT NOT NULL
                    CHECK (currency IN ('SGD', 'USD', 'EUR', 'GBP'))
            )
            """
        )


def save_transactions(
    df: pd.DataFrame,
    db_path: Path = DB_PATH,
) -> int:
    """
    Save validated transactions to the database.

    Returns the number of rows inserted.
    """
    if df.empty:
        return 0

    columns = [
        "transaction_id",
        "date",
        "description",
        "vendor",
        "amount",
        "transaction_type",
        "category",
        "department",
        "currency",
    ]

    records = df[columns].copy()

    records["date"] = records["date"].dt.strftime("%Y-%m-%d")

    with get_connection(db_path) as conn:
        records.to_sql(
            "transactions",
            conn,
            if_exists="append",
            index=False,
        )

    return len(records)
