from pathlib import Path

import pandas as pd

from src.database import (
    get_connection,
)
from src.pipeline import (
    process_financial_file,
)


def test_pipeline_processes_mapped_csv(
    tmp_path: Path,
):
    """
    Test the full FinPilot pipeline using
    customer-style column names.
    """

    csv_path = (
        tmp_path
        / "customer_transactions.csv"
    )

    test_db = (
        tmp_path
        / "finpilot_pipeline.db"
    )

    df = pd.DataFrame(
        [
            {
                "Document Number": "T001",
                "Posting Date": "2026-09-01",
                "Supplier": "AWS",
                "Gross Amount": 15000,
                "Currency": "SGD",
            },
            {
                "Document Number": "T002",
                "Posting Date": "2026-09-02",
                "Supplier": "Google",
                "Gross Amount": 500,
                "Currency": "SGD",
            },
        ]
    )

    df.to_csv(
        csv_path,
        index=False,
    )

    mapping = {
        "Document Number": (
            "transaction_id"
        ),
        "Posting Date": "date",
        "Supplier": "vendor",
        "Gross Amount": "amount",
        "Currency": "currency",
    }

    result = (
        process_financial_file(
            csv_path,
            mapping=mapping,
            db_path=test_db,
            high_value_thresholds={
                "SGD": 10000,
            },
        )
    )

    assert result["raw_rows"] == 2
    assert result["valid_rows"] == 2
    assert result["invalid_rows"] == 0

    assert (
        result[
            "transactions_inserted"
        ]
        == 2
    )

    assert (
        result[
            "signals_generated"
        ]
        == 1
    )

    assert (
        result[
            "exceptions_created"
        ]
        == 1
    )

    assert (
        result[
            "signal_counts"
        ]
        == {
            "HIGH_VALUE": 1,
        }
    )


def test_pipeline_handles_invalid_rows(
    tmp_path: Path,
):
    """
    Invalid rows should be separated from valid rows
    rather than crashing the complete processing run.
    """

    csv_path = (
        tmp_path
        / "customer_transactions.csv"
    )

    test_db = (
        tmp_path
        / "finpilot_pipeline.db"
    )

    df = pd.DataFrame(
        [
            {
                "Document Number": "T001",
                "Posting Date": "2026-09-01",
                "Gross Amount": 15000,
                "Currency": "SGD",
            },
            {
                "Document Number": "T002",
                "Posting Date": "BAD_DATE",
                "Gross Amount": -100,
                "Currency": "SGD",
            },
        ]
    )

    df.to_csv(
        csv_path,
        index=False,
    )

    mapping = {
        "Document Number": (
            "transaction_id"
        ),
        "Posting Date": "date",
        "Gross Amount": "amount",
        "Currency": "currency",
    }

    result = (
        process_financial_file(
            csv_path,
            mapping=mapping,
            db_path=test_db,
            high_value_thresholds={
                "SGD": 10000,
            },
        )
    )

    assert result["raw_rows"] == 2
    assert result["valid_rows"] == 1
    assert result["invalid_rows"] == 1

    assert (
        len(
            result[
                "invalid_df"
            ]
        )
        == 1
    )


def test_pipeline_persists_database_state(
    tmp_path: Path,
):
    """
    Verify that the pipeline creates trusted transactions,
    exceptions and signals in SQLite.
    """

    csv_path = (
        tmp_path
        / "customer_transactions.csv"
    )

    test_db = (
        tmp_path
        / "finpilot_pipeline.db"
    )

    df = pd.DataFrame(
        [
            {
                "ID": "T001",
                "Date": "2026-09-01",
                "Vendor Name": "AWS",
                "Amount": 20000,
                "Currency": "SGD",
            }
        ]
    )

    df.to_csv(
        csv_path,
        index=False,
    )

    mapping = {
        "ID": "transaction_id",
        "Date": "date",
        "Vendor Name": "vendor",
        "Amount": "amount",
        "Currency": "currency",
    }

    process_financial_file(
        csv_path,
        mapping=mapping,
        db_path=test_db,
        high_value_thresholds={
            "SGD": 10000,
        },
    )

    with get_connection(
        test_db
    ) as conn:

        transaction_count = (
            conn.execute(
                """
                SELECT COUNT(*)
                FROM transactions
                """
            )
            .fetchone()[0]
        )

        exception_count = (
            conn.execute(
                """
                SELECT COUNT(*)
                FROM exceptions
                """
            )
            .fetchone()[0]
        )

        signal_count = (
            conn.execute(
                """
                SELECT COUNT(*)
                FROM exception_signals
                """
            )
            .fetchone()[0]
        )

    assert transaction_count == 1
    assert exception_count == 1
    assert signal_count == 1