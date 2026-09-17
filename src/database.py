from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


DB_PATH = Path("finpilot.db")


def get_connection(
    db_path: Path = DB_PATH,
) -> sqlite3.Connection:
    """
    Create and return a connection to the FinPilot
    SQLite database.

    Foreign-key enforcement is enabled for every
    connection.
    """

    conn = sqlite3.connect(
        db_path
    )

    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    return conn


def initialize_database(
    db_path: Path = DB_PATH,
) -> None:
    """
    Create all FinPilot database tables if they do
    not already exist.

    Core transaction fields are required.

    Optional transaction fields may be NULL because
    different finance systems provide different levels
    of detail.
    """

    with get_connection(
        db_path
    ) as conn:

        # =================================================
        # 1. TRANSACTIONS
        # =================================================

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id TEXT PRIMARY KEY,

                date TEXT NOT NULL,

                description TEXT,

                vendor TEXT,

                amount REAL NOT NULL
                    CHECK (amount > 0),

                transaction_type TEXT
                    CHECK (
                        transaction_type IS NULL
                        OR transaction_type IN (
                            'revenue',
                            'expense'
                        )
                    ),

                category TEXT,

                department TEXT,

                currency TEXT NOT NULL
                    CHECK (
                        currency IN (
                            'SGD',
                            'USD',
                            'EUR',
                            'GBP'
                        )
                    )
            )
            """
        )

        # =================================================
        # 2. EXCEPTIONS
        # =================================================

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS exceptions (
                exception_id TEXT PRIMARY KEY,

                transaction_id TEXT NOT NULL,

                priority TEXT NOT NULL
                    CHECK (
                        priority IN (
                            'LOW',
                            'MEDIUM',
                            'HIGH'
                        )
                    ),

                status TEXT NOT NULL
                    DEFAULT 'OPEN'
                    CHECK (
                        status IN (
                            'OPEN',
                            'CLEARED',
                            'CONFIRMED_ISSUE',
                            'NEEDS_INFO'
                        )
                    ),

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                updated_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (
                    transaction_id
                )
                    REFERENCES transactions(
                        transaction_id
                    )
            )
            """
        )

        # =================================================
        # 3. EXCEPTION SIGNALS
        # =================================================

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS exception_signals (
                signal_id TEXT PRIMARY KEY,

                exception_id TEXT NOT NULL,

                transaction_id TEXT NOT NULL,

                signal_type TEXT NOT NULL
                    CHECK (
                        TRIM(signal_type) <> ''
                    ),

                source TEXT NOT NULL
                    CHECK (
                        source IN (
                            'RULE',
                            'ML'
                        )
                    ),

                severity TEXT NOT NULL
                    CHECK (
                        severity IN (
                            'LOW',
                            'MEDIUM',
                            'HIGH'
                        )
                    ),

                score REAL,

                reason TEXT NOT NULL
                    CHECK (
                        TRIM(reason) <> ''
                    ),

                evidence TEXT NOT NULL,

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (
                    exception_id
                )
                    REFERENCES exceptions(
                        exception_id
                    ),

                FOREIGN KEY (
                    transaction_id
                )
                    REFERENCES transactions(
                        transaction_id
                    )
            )
            """
        )


def save_transactions(
    df: pd.DataFrame,
    db_path: Path = DB_PATH,
) -> int:
    """
    Save validated FinPilot transactions.

    Optional fields may contain NULL values.

    Returns
    -------
    int
        Number of rows inserted.
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

    records = (
        df[
            columns
        ]
        .copy()
    )

    # Validation converts valid dates to Pandas
    # datetime values. SQLite stores them as
    # YYYY-MM-DD text in V1.

    records["date"] = (
        records["date"]
        .dt.strftime(
            "%Y-%m-%d"
        )
    )

    # Pandas can represent missing values using NaN,
    # NaT or pd.NA.
    #
    # SQLite expects Python None when storing SQL NULL.

    optional_columns = [
        "description",
        "vendor",
        "transaction_type",
        "category",
        "department",
    ]

    for column in optional_columns:

        records[column] = (
            records[column]
            .where(
                records[column].notna(),
                None,
            )
        )

    with get_connection(
        db_path
    ) as conn:

        records.to_sql(
            "transactions",
            conn,
            if_exists="append",
            index=False,
        )

    return len(records)