from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd


DEFAULT_HIGH_VALUE_THRESHOLDS = {
    "SGD": 10_000.00,
    "USD": 10_000.00,
    "EUR": 10_000.00,
    "GBP": 10_000.00,
}


CONTROL_REQUIREMENTS = {
    "HIGH_VALUE": {
        "amount",
        "currency",
    },
    "DUPLICATE_CANDIDATE": {
        "date",
        "vendor",
        "amount",
    },
}


def get_control_capabilities(
    df: pd.DataFrame,
) -> dict[str, dict[str, Any]]:
    """
    Return which FinPilot controls are available
    for the current mapped dataset.
    """

    available_columns = set(df.columns)

    capabilities: dict[
        str,
        dict[str, Any],
    ] = {}

    for control_name, required_fields in (
        CONTROL_REQUIREMENTS.items()
    ):
        missing_fields = sorted(
            required_fields
            - available_columns
        )

        capabilities[control_name] = {
            "available": (
                len(missing_fields) == 0
            ),
            "required_fields": sorted(
                required_fields
            ),
            "missing_fields": (
                missing_fields
            ),
        }

    return capabilities


def detect_high_value_transactions(
    df: pd.DataFrame,
    thresholds: Mapping[str, float] | None = None,
) -> list[dict[str, Any]]:
    """
    Detect transactions above the configured
    currency threshold.
    """

    if thresholds is None:
        thresholds = (
            DEFAULT_HIGH_VALUE_THRESHOLDS
        )

    required_fields = (
        CONTROL_REQUIREMENTS[
            "HIGH_VALUE"
        ]
    )

    if not required_fields.issubset(
        df.columns
    ):
        return []

    signals: list[dict[str, Any]] = []

    for _, transaction in df.iterrows():

        transaction_id = str(
            transaction[
                "transaction_id"
            ]
        )

        currency_value = (
            transaction["currency"]
        )

        amount_value = (
            transaction["amount"]
        )

        if (
            pd.isna(currency_value)
            or pd.isna(amount_value)
        ):
            continue

        currency = str(
            currency_value
        ).upper()

        amount = float(
            amount_value
        )

        if currency not in thresholds:
            continue

        threshold = float(
            thresholds[currency]
        )

        if amount <= threshold:
            continue

        signals.append(
            {
                "transaction_id": (
                    transaction_id
                ),
                "signal_type": (
                    "HIGH_VALUE"
                ),
                "source": "RULE",
                "severity": "HIGH",
                "score": None,
                "reason": (
                    "Transaction exceeds the "
                    "configured high-value threshold."
                ),
                "evidence": {
                    "amount": amount,
                    "threshold": threshold,
                    "currency": currency,
                },
            }
        )

    return signals


def detect_duplicate_candidates(
    df: pd.DataFrame,
) -> list[dict[str, Any]]:
    """
    Detect duplicate candidates using:

    - same date
    - same vendor
    - same amount

    Rows with missing comparison data are skipped.
    """

    if df.empty:
        return []

    required_fields = (
        CONTROL_REQUIREMENTS[
            "DUPLICATE_CANDIDATE"
        ]
    )

    if not required_fields.issubset(
        df.columns
    ):
        return []

    working_df = df.copy()

    usable_mask = (
        working_df["date"].notna()
        & working_df["vendor"].notna()
        & working_df["amount"].notna()
    )

    working_df = (
        working_df.loc[
            usable_mask
        ]
        .copy()
    )

    if working_df.empty:
        return []

    vendor_not_blank = (
        working_df["vendor"]
        .astype(str)
        .str.strip()
        .ne("")
    )

    working_df = (
        working_df.loc[
            vendor_not_blank
        ]
        .copy()
    )

    if working_df.empty:
        return []

    working_df[
        "_duplicate_date"
    ] = pd.to_datetime(
        working_df["date"],
        errors="coerce",
    ).dt.strftime("%Y-%m-%d")

    working_df[
        "_duplicate_vendor"
    ] = (
        working_df["vendor"]
        .astype(str)
        .str.strip()
        .str.casefold()
    )

    working_df[
        "_duplicate_amount"
    ] = pd.to_numeric(
        working_df["amount"],
        errors="coerce",
    )

    valid_comparison_mask = (
        working_df[
            "_duplicate_date"
        ].notna()
        & working_df[
            "_duplicate_amount"
        ].notna()
    )

    working_df = (
        working_df.loc[
            valid_comparison_mask
        ]
        .copy()
    )

    if working_df.empty:
        return []

    duplicate_columns = [
        "_duplicate_date",
        "_duplicate_vendor",
        "_duplicate_amount",
    ]

    duplicate_mask = (
        working_df.duplicated(
            subset=duplicate_columns,
            keep=False,
        )
    )

    duplicate_df = (
        working_df.loc[
            duplicate_mask
        ]
        .copy()
    )

    if duplicate_df.empty:
        return []

    signals: list[dict[str, Any]] = []

    grouped = duplicate_df.groupby(
        duplicate_columns,
        dropna=False,
        sort=False,
    )

    for _, group in grouped:

        transaction_ids = (
            group["transaction_id"]
            .astype(str)
            .drop_duplicates()
            .tolist()
        )

        if len(transaction_ids) < 2:
            continue

        for _, transaction in (
            group.iterrows()
        ):

            transaction_id = str(
                transaction[
                    "transaction_id"
                ]
            )

            candidate_transaction_ids = [
                candidate_id
                for candidate_id
                in transaction_ids
                if candidate_id
                != transaction_id
            ]

            if not candidate_transaction_ids:
                continue

            signals.append(
                {
                    "transaction_id": (
                        transaction_id
                    ),
                    "signal_type": (
                        "DUPLICATE_CANDIDATE"
                    ),
                    "source": "RULE",
                    "severity": "HIGH",
                    "score": None,
                    "reason": (
                        "Transaction matches "
                        "another transaction "
                        "on vendor, amount and date."
                    ),
                    "evidence": {
                        "vendor": str(
                            transaction[
                                "vendor"
                            ]
                        ),
                        "amount": float(
                            transaction[
                                "amount"
                            ]
                        ),
                        "date": (
                            transaction[
                                "_duplicate_date"
                            ]
                        ),
                        "candidate_transaction_ids": (
                            candidate_transaction_ids
                        ),
                    },
                }
            )

    return signals


def run_financial_controls(
    df: pd.DataFrame,
    high_value_thresholds: Mapping[
        str,
        float,
    ] | None = None,
) -> list[dict[str, Any]]:
    """
    Run all currently available deterministic
    FinPilot controls.
    """

    signals: list[dict[str, Any]] = []

    capabilities = (
        get_control_capabilities(df)
    )

    if capabilities[
        "HIGH_VALUE"
    ]["available"]:

        signals.extend(
            detect_high_value_transactions(
                df,
                thresholds=(
                    high_value_thresholds
                ),
            )
        )

    if capabilities[
        "DUPLICATE_CANDIDATE"
    ]["available"]:

        signals.extend(
            detect_duplicate_candidates(
                df
            )
        )

    return signals