from pathlib import Path

import pandas as pd

from src.controls import run_financial_controls
from src.database import (
    get_connection,
    initialize_database,
    save_transactions,
)
from src.exceptions import persist_exception_signals
from src.validation import validate_transactions


def test_complete_financial_exception_workflow(
    tmp_path: Path,
):
    """
    Test the complete FinPilot V1 backend workflow:

    CSV
        ↓
    validation
        ↓
    trusted transactions
        ↓
    SQLite
        ↓
    deterministic financial controls
        ↓
    exception signals
        ↓
    persisted exceptions
        ↓
    persisted exception signals
    """

    # =====================================================
    # 1. CREATE TEMPORARY DATABASE
    # =====================================================

    test_db = tmp_path / "finpilot_integration.db"

    initialize_database(test_db)

    # =====================================================
    # 2. LOAD SAMPLE TRANSACTIONS
    # =====================================================

    raw_df = pd.read_csv(
        "data/sample_transactions.csv"
    )

    assert len(raw_df) == 10

    # =====================================================
    # 3. VALIDATE TRANSACTIONS
    # =====================================================

    valid_df, invalid_df = validate_transactions(
        raw_df
    )

    assert len(valid_df) == 10
    assert len(invalid_df) == 0

    # =====================================================
    # 4. SAVE TRUSTED TRANSACTIONS
    # =====================================================

    inserted_transactions = save_transactions(
        valid_df,
        test_db,
    )

    assert inserted_transactions == 10

    # =====================================================
    # 5. RUN DETERMINISTIC FINANCIAL CONTROLS
    # =====================================================

    signals = run_financial_controls(
        valid_df,
        high_value_thresholds={
            "SGD": 10000.00,
            "USD": 10000.00,
            "EUR": 10000.00,
            "GBP": 10000.00,
        },
    )

    # Sample data contains one transaction above
    # the SGD 10,000 threshold:
    #
    # T0006 = SGD 12,000
    #
    # There are no exact duplicate candidates.

    assert len(signals) == 1

    signal = signals[0]

    assert signal["transaction_id"] == "T0006"
    assert signal["signal_type"] == "HIGH_VALUE"
    assert signal["source"] == "RULE"
    assert signal["severity"] == "HIGH"

    # =====================================================
    # 6. PERSIST EXCEPTIONS
    # =====================================================

    persistence_result = (
        persist_exception_signals(
            signals,
            test_db,
        )
    )

    assert persistence_result == {
        "exceptions_created": 1,
        "signals_created": 1,
    }

    # =====================================================
    # 7. VERIFY DATABASE STATE
    # =====================================================

    with get_connection(test_db) as conn:

        transaction_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM transactions
            """
        ).fetchone()[0]

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

    assert transaction_count == 10
    assert exception_count == 1
    assert signal_count == 1

    # =====================================================
    # 8. VERIFY COMPLETE RELATIONSHIP
    # =====================================================

    with get_connection(test_db) as conn:

        result = conn.execute(
            """
            SELECT
                t.transaction_id,
                t.vendor,
                t.amount,
                t.currency,

                e.exception_id,
                e.priority,
                e.status,

                s.signal_type,
                s.source,
                s.severity

            FROM transactions AS t

            JOIN exceptions AS e
                ON t.transaction_id =
                   e.transaction_id

            JOIN exception_signals AS s
                ON e.exception_id =
                   s.exception_id

            WHERE t.transaction_id = ?
            """,
            ("T0006",),
        ).fetchone()

    assert result is not None

    assert result[0] == "T0006"
    assert result[1] == "XYZ Pte Ltd"
    assert result[2] == 12000.00
    assert result[3] == "SGD"

    assert result[4].startswith("EXC_")
    assert result[5] == "HIGH"
    assert result[6] == "OPEN"

    assert result[7] == "HIGH_VALUE"
    assert result[8] == "RULE"
    assert result[9] == "HIGH"