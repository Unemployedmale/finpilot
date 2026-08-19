from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd


# =========================================================
# CONFIGURATION
# =========================================================

# V1 demonstration thresholds.
#
# These are configured per currency so the control does not
# silently assume that all currencies are the same.
#
# For a production system, these thresholds would normally
# be configured by the finance team and could vary by
# company, entity, department or transaction type.
DEFAULT_HIGH_VALUE_THRESHOLDS = {
    "SGD": 10_000.00,
    "USD": 10_000.00,
    "EUR": 10_000.00,
    "GBP": 10_000.00,
}


# =========================================================
# HIGH-VALUE CONTROL
# =========================================================

def detect_high_value_transactions(
    df: pd.DataFrame,
    thresholds: Mapping[str, float] | None = None,
) -> list[dict[str, Any]]:
    """
    Detect transactions whose amount exceeds the configured
    threshold for their currency.

    Parameters
    ----------
    df:
        Validated transaction DataFrame.

    thresholds:
        Mapping of currency codes to high-value thresholds.

        Example:
        {
            "SGD": 10000,
            "USD": 8000,
        }

    Returns
    -------
    list[dict]
        Standardised FinPilot exception signals.
    """

    if thresholds is None:
        thresholds = DEFAULT_HIGH_VALUE_THRESHOLDS

    signals: list[dict[str, Any]] = []

    for _, transaction in df.iterrows():

        transaction_id = str(transaction["transaction_id"])
        currency = str(transaction["currency"]).upper()
        amount = float(transaction["amount"])

        # If no threshold has been configured for the currency,
        # FinPilot does not make up one.
        if currency not in thresholds:
            continue

        threshold = float(thresholds[currency])

        # Important:
        # The rule is strictly greater than the threshold.
        #
        # Example:
        # 10,000 threshold
        # 10,000 transaction -> no signal
        # 10,001 transaction -> signal
        if amount <= threshold:
            continue

        signal = {
            "transaction_id": transaction_id,
            "signal_type": "HIGH_VALUE",
            "source": "RULE",
            "severity": "HIGH",
            "score": None,
            "reason": (
                "Transaction exceeds the configured "
                "high-value threshold."
            ),
            "evidence": {
                "amount": amount,
                "threshold": threshold,
                "currency": currency,
            },
        }

        signals.append(signal)

    return signals


# =========================================================
# DUPLICATE-CANDIDATE CONTROL
# =========================================================

def detect_duplicate_candidates(
    df: pd.DataFrame,
) -> list[dict[str, Any]]:
    """
    Detect transactions that may represent duplicate
    financial activity.

    Two or more transactions are treated as duplicate
    candidates when they have:

    - different transaction IDs
    - the same date
    - the same vendor
    - the same amount

    This control does NOT claim that the transactions are
    confirmed duplicates.

    It only creates evidence for human review.
    """

    if df.empty:
        return []

    working_df = df.copy()

    # -----------------------------------------------------
    # Normalise values used for comparison
    # -----------------------------------------------------

    working_df["_duplicate_date"] = pd.to_datetime(
        working_df["date"],
        errors="coerce",
    ).dt.strftime("%Y-%m-%d")

    working_df["_duplicate_vendor"] = (
        working_df["vendor"]
        .astype(str)
        .str.strip()
        .str.casefold()
    )

    working_df["_duplicate_amount"] = pd.to_numeric(
        working_df["amount"],
        errors="coerce",
    )

    duplicate_columns = [
        "_duplicate_date",
        "_duplicate_vendor",
        "_duplicate_amount",
    ]

    # Keep every member of a duplicate group.
    duplicate_mask = working_df.duplicated(
        subset=duplicate_columns,
        keep=False,
    )

    duplicate_df = working_df.loc[duplicate_mask].copy()

    if duplicate_df.empty:
        return []

    signals: list[dict[str, Any]] = []

    grouped = duplicate_df.groupby(
        duplicate_columns,
        dropna=False,
        sort=False,
    )

    for _, group in grouped:

        # A duplicate group must contain at least two
        # different transaction IDs.
        transaction_ids = (
            group["transaction_id"]
            .astype(str)
            .drop_duplicates()
            .tolist()
        )

        if len(transaction_ids) < 2:
            continue

        for _, transaction in group.iterrows():

            transaction_id = str(
                transaction["transaction_id"]
            )

            candidate_transaction_ids = [
                candidate_id
                for candidate_id in transaction_ids
                if candidate_id != transaction_id
            ]

            # Defensive check.
            if not candidate_transaction_ids:
                continue

            signal = {
                "transaction_id": transaction_id,
                "signal_type": "DUPLICATE_CANDIDATE",
                "source": "RULE",
                "severity": "HIGH",
                "score": None,
                "reason": (
                    "Transaction matches another transaction "
                    "on vendor, amount and date."
                ),
                "evidence": {
                    "vendor": str(transaction["vendor"]),
                    "amount": float(transaction["amount"]),
                    "date": transaction[
                        "_duplicate_date"
                    ],
                    "candidate_transaction_ids": (
                        candidate_transaction_ids
                    ),
                },
            }

            signals.append(signal)

    return signals


# =========================================================
# CONTROL ORCHESTRATOR
# =========================================================

def run_financial_controls(
    df: pd.DataFrame,
    high_value_thresholds: Mapping[str, float] | None = None,
) -> list[dict[str, Any]]:
    """
    Run all deterministic V1 financial controls.

    The controls currently include:

    1. HIGH_VALUE
    2. DUPLICATE_CANDIDATE

    All controls return signals using the same standard
    FinPilot signal structure.
    """

    signals: list[dict[str, Any]] = []

    high_value_signals = detect_high_value_transactions(
        df,
        thresholds=high_value_thresholds,
    )

    duplicate_signals = detect_duplicate_candidates(df)

    signals.extend(high_value_signals)
    signals.extend(duplicate_signals)

    return signals
