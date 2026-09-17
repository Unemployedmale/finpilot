from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, BinaryIO

import pandas as pd

from src.controls import run_financial_controls
from src.database import (
    DB_PATH,
    initialize_database,
    save_transactions,
)
from src.exceptions import persist_exception_signals
from src.ingestion import load_financial_file
from src.mapping import apply_column_mapping
from src.validation import validate_transactions


def process_financial_file(
    source: str | Path | BinaryIO,
    mapping: Mapping[str, str],
    filename: str | None = None,
    db_path: Path = DB_PATH,
    high_value_thresholds: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """
    Run the complete FinPilot V1 processing pipeline.

    Workflow
    --------
    1. Load CSV/XLSX
    2. Apply source-to-canonical column mapping
    3. Validate transactions
    4. Initialize database
    5. Save trusted transactions
    6. Run deterministic financial controls
    7. Persist exceptions and signals

    Returns
    -------
    dict[str, Any]
        Summary of the complete processing run.
    """

    # =====================================================
    # 1. LOAD SOURCE FILE
    # =====================================================

    raw_df = load_financial_file(
        source,
        filename=filename,
    )

    # =====================================================
    # 2. APPLY COLUMN MAPPING
    # =====================================================

    mapped_df = apply_column_mapping(
        raw_df,
        mapping,
    )

    # =====================================================
    # 3. VALIDATE TRANSACTIONS
    # =====================================================

    valid_df, invalid_df = (
        validate_transactions(
            mapped_df
        )
    )

    # =====================================================
    # 4. INITIALIZE DATABASE
    # =====================================================

    initialize_database(
        db_path
    )

    # =====================================================
    # 5. SAVE VALID TRANSACTIONS
    # =====================================================

    inserted_transactions = (
        save_transactions(
            valid_df,
            db_path,
        )
    )

    # =====================================================
    # 6. RUN FINANCIAL CONTROLS
    # =====================================================

    signals = run_financial_controls(
        valid_df,
        high_value_thresholds=(
            high_value_thresholds
        ),
    )

    # =====================================================
    # 7. PERSIST EXCEPTIONS
    # =====================================================

    persistence_result = (
        persist_exception_signals(
            signals,
            db_path,
        )
    )

    # =====================================================
    # 8. SIGNAL BREAKDOWN
    # =====================================================

    signal_counts: dict[str, int] = {}

    for signal in signals:

        signal_type = str(
            signal["signal_type"]
        )

        signal_counts[
            signal_type
        ] = (
            signal_counts.get(
                signal_type,
                0,
            )
            + 1
        )

    # =====================================================
    # 9. RETURN PIPELINE RESULT
    # =====================================================

    return {
        "raw_rows": len(raw_df),
        "valid_rows": len(valid_df),
        "invalid_rows": len(invalid_df),
        "transactions_inserted": (
            inserted_transactions
        ),
        "signals_generated": len(signals),
        "exceptions_created": (
            persistence_result[
                "exceptions_created"
            ]
        ),
        "signals_created": (
            persistence_result[
                "signals_created"
            ]
        ),
        "signal_counts": signal_counts,
        "valid_df": valid_df,
        "invalid_df": invalid_df,
        "signals": signals,
    }