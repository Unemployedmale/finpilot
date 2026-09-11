from __future__ import annotations

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


# =========================================================
# CONFIGURATION
# =========================================================

DATA_PATH = Path(
    "data/private/finpilot_ap_test_1000.csv"
)

TEST_DB_PATH = Path(
    "/tmp/finpilot_ap_1000_evaluation.db"
)

CANONICAL_COLUMNS = [
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


# =========================================================
# METRIC HELPERS
# =========================================================

def calculate_metrics(
    predicted_ids: set[str],
    expected_ids: set[str],
) -> dict[str, float | int]:
    """
    Compare FinPilot predictions against known
    synthetic ground truth.
    """

    true_positives = len(
        predicted_ids & expected_ids
    )

    false_positives = len(
        predicted_ids - expected_ids
    )

    false_negatives = len(
        expected_ids - predicted_ids
    )

    precision = (
        true_positives
        / (true_positives + false_positives)
        if true_positives + false_positives > 0
        else 0.0
    )

    recall = (
        true_positives
        / (true_positives + false_negatives)
        if true_positives + false_negatives > 0
        else 0.0
    )

    return {
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "precision": precision,
        "recall": recall,
    }


def print_metrics(
    name: str,
    metrics: dict[str, float | int],
) -> None:
    """
    Print evaluation metrics clearly.
    """

    print()
    print(name)
    print("-" * 60)

    print(
        "True positives: ",
        metrics["true_positives"],
    )

    print(
        "False positives:",
        metrics["false_positives"],
    )

    print(
        "False negatives:",
        metrics["false_negatives"],
    )

    print(
        "Precision:      ",
        f'{metrics["precision"]:.2%}',
    )

    print(
        "Recall:         ",
        f'{metrics["recall"]:.2%}',
    )


# =========================================================
# MAIN EVALUATION
# =========================================================

def main() -> None:

    print()
    print("=" * 70)
    print("FINPILOT V1 — 1,000 TRANSACTION EVALUATION")
    print("=" * 70)

    # -----------------------------------------------------
    # 1. LOAD DATA
    # -----------------------------------------------------

    print()
    print("1. Loading dataset...")

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_PATH}"
        )

    raw_df = pd.read_csv(
        DATA_PATH
    )

    print(
        f"Raw transactions: {len(raw_df):,}"
    )

    # -----------------------------------------------------
    # 2. KEEP FINPILOT INPUT COLUMNS
    # -----------------------------------------------------

    missing_columns = [
        column
        for column in CANONICAL_COLUMNS
        if column not in raw_df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Dataset is missing FinPilot columns: "
            f"{missing_columns}"
        )

    input_df = raw_df[
        CANONICAL_COLUMNS
    ].copy()

    # -----------------------------------------------------
    # 3. VALIDATE DATA
    # -----------------------------------------------------

    print()
    print("2. Running FinPilot validation...")

    valid_df, invalid_df = (
        validate_transactions(
            input_df
        )
    )

    print(
        f"Valid transactions:   {len(valid_df):,}"
    )

    print(
        f"Invalid transactions: {len(invalid_df):,}"
    )

    # -----------------------------------------------------
    # 4. CREATE CLEAN TEMPORARY DATABASE
    # -----------------------------------------------------

    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    initialize_database(
        TEST_DB_PATH
    )

    # -----------------------------------------------------
    # 5. SAVE TRUSTED TRANSACTIONS
    # -----------------------------------------------------

    print()
    print("3. Saving trusted transactions...")

    inserted_transactions = (
        save_transactions(
            valid_df,
            TEST_DB_PATH,
        )
    )

    print(
        f"Transactions inserted: "
        f"{inserted_transactions:,}"
    )

    # -----------------------------------------------------
    # 6. RUN CURRENT FINANCIAL CONTROLS
    # -----------------------------------------------------

    print()
    print("4. Running financial controls...")

    signals = run_financial_controls(
        valid_df
    )

    high_value_signals = [
        signal
        for signal in signals
        if signal["signal_type"]
        == "HIGH_VALUE"
    ]

    duplicate_signals = [
        signal
        for signal in signals
        if signal["signal_type"]
        == "DUPLICATE_CANDIDATE"
    ]

    print(
        f"HIGH_VALUE signals: "
        f"{len(high_value_signals):,}"
    )

    print(
        f"DUPLICATE_CANDIDATE signals: "
        f"{len(duplicate_signals):,}"
    )

    print(
        f"Total signals: "
        f"{len(signals):,}"
    )

    # -----------------------------------------------------
    # 7. LOAD SYNTHETIC GROUND TRUTH
    # -----------------------------------------------------

    print()
    print("5. Comparing against known ground truth...")

    expected_high_value_ids = set(
        raw_df.loc[
            raw_df["expected_high_value"],
            "transaction_id",
        ].astype(str)
    )

    expected_duplicate_ids = set(
        raw_df.loc[
            raw_df[
                "expected_duplicate_candidate"
            ],
            "transaction_id",
        ].astype(str)
    )

    predicted_high_value_ids = {
        str(signal["transaction_id"])
        for signal in high_value_signals
    }

    predicted_duplicate_ids = {
        str(signal["transaction_id"])
        for signal in duplicate_signals
    }

    # -----------------------------------------------------
    # 8. HIGH-VALUE METRICS
    # -----------------------------------------------------

    high_value_metrics = (
        calculate_metrics(
            predicted_high_value_ids,
            expected_high_value_ids,
        )
    )

    print_metrics(
        "HIGH_VALUE RESULTS",
        high_value_metrics,
    )

    # -----------------------------------------------------
    # 9. DUPLICATE METRICS
    # -----------------------------------------------------

    duplicate_metrics = (
        calculate_metrics(
            predicted_duplicate_ids,
            expected_duplicate_ids,
        )
    )

    print_metrics(
        "DUPLICATE_CANDIDATE RESULTS",
        duplicate_metrics,
    )

    # -----------------------------------------------------
    # 10. OVERALL CURRENT V1 METRICS
    # -----------------------------------------------------

    predicted_exception_ids = (
        predicted_high_value_ids
        | predicted_duplicate_ids
    )

    expected_exception_ids = (
        expected_high_value_ids
        | expected_duplicate_ids
    )

    overall_metrics = (
        calculate_metrics(
            predicted_exception_ids,
            expected_exception_ids,
        )
    )

    print_metrics(
        "OVERALL CURRENT V1 RESULTS",
        overall_metrics,
    )

    # -----------------------------------------------------
    # 11. PERSIST EXCEPTIONS
    # -----------------------------------------------------

    print()
    print("6. Persisting exceptions...")

    persistence_result = (
        persist_exception_signals(
            signals,
            TEST_DB_PATH,
        )
    )

    print(
        "Exceptions created:",
        persistence_result[
            "exceptions_created"
        ],
    )

    print(
        "Signals created:",
        persistence_result[
            "signals_created"
        ],
    )

    # -----------------------------------------------------
    # 12. VERIFY SQLITE COUNTS
    # -----------------------------------------------------

    with get_connection(
        TEST_DB_PATH
    ) as conn:

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

    print()
    print("7. Database state")
    print("-" * 60)

    print(
        f"Transactions: {transaction_count:,}"
    )

    print(
        f"Exceptions:   {exception_count:,}"
    )

    print(
        f"Signals:      {signal_count:,}"
    )

    # -----------------------------------------------------
    # 13. IDEMPOTENCY TEST
    # -----------------------------------------------------

    print()
    print("8. Testing repeated execution...")

    second_run = (
        persist_exception_signals(
            signals,
            TEST_DB_PATH,
        )
    )

    print(
        "Second-run exceptions created:",
        second_run[
            "exceptions_created"
        ],
    )

    print(
        "Second-run signals created:",
        second_run[
            "signals_created"
        ],
    )

    # -----------------------------------------------------
    # 14. HARD EXPECTATIONS
    # -----------------------------------------------------

    print()
    print("9. Checking expected results...")

    assert len(raw_df) == 1000

    assert len(valid_df) == 1000
    assert len(invalid_df) == 0

    assert inserted_transactions == 1000

    assert len(
        expected_high_value_ids
    ) == 30

    assert len(
        expected_duplicate_ids
    ) == 40

    assert len(
        high_value_signals
    ) == 30

    assert len(
        duplicate_signals
    ) == 40

    assert len(signals) == 70

    assert (
        high_value_metrics[
            "false_positives"
        ]
        == 0
    )

    assert (
        high_value_metrics[
            "false_negatives"
        ]
        == 0
    )

    assert (
        duplicate_metrics[
            "false_positives"
        ]
        == 0
    )

    assert (
        duplicate_metrics[
            "false_negatives"
        ]
        == 0
    )

    assert transaction_count == 1000
    assert exception_count == 70
    assert signal_count == 70

    assert second_run == {
        "exceptions_created": 0,
        "signals_created": 0,
    }

    # -----------------------------------------------------
    # SUCCESS
    # -----------------------------------------------------

    print()
    print("=" * 70)
    print("SUCCESS — FINPILOT V1 PASSED THE 1,000-ROW TEST")
    print("=" * 70)

    print()
    print(
        "Expected current exceptions: 70"
    )

    print(
        "Detected current exceptions: 70"
    )

    print(
        "HIGH_VALUE precision: 100%"
    )

    print(
        "HIGH_VALUE recall:    100%"
    )

    print(
        "DUPLICATE precision:  100%"
    )

    print(
        "DUPLICATE recall:     100%"
    )

    print()

    # Remove temporary evaluation database.
    TEST_DB_PATH.unlink(
        missing_ok=True
    )


if __name__ == "__main__":
    main()