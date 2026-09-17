from __future__ import annotations

import pandas as pd

from src.schema import (
    ALLOWED_CURRENCIES,
    ALLOWED_TRANSACTION_TYPES,
    CORE_REQUIRED_FIELDS,
    OPTIONAL_FIELDS,
)


def validate_required_columns(
    df: pd.DataFrame,
) -> list[str]:
    """
    Return required FinPilot fields missing from a DataFrame.

    Only core canonical fields are globally required.
    Optional fields may be unavailable depending on the
    customer's accounting or transaction source.
    """

    return [
        column
        for column in CORE_REQUIRED_FIELDS
        if column not in df.columns
    ]


def ensure_optional_columns(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Add missing optional canonical fields as null values.

    This allows FinPilot to accept different finance exports
    without inventing business information that was not
    supplied by the source system.
    """

    df = df.copy()

    for column in OPTIONAL_FIELDS:

        if column not in df.columns:
            df[column] = None

    return df


def validate_transactions(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Validate transactions after they have been mapped into
    FinPilot's canonical schema.

    Returns
    -------
    valid_df:
        Rows that pass all core validation rules.

    invalid_df:
        Rows that fail at least one core validation rule.
        Includes a validation_errors column.

    Notes
    -----
    Optional fields do not make an entire transaction
    invalid simply because the source system does not
    provide them.

    Individual financial controls may require additional
    fields.
    """

    df = df.copy()

    # =====================================================
    # REQUIRED COLUMN CHECK
    # =====================================================

    missing_columns = validate_required_columns(
        df
    )

    if missing_columns:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(missing_columns)
        )

    # Add optional fields that the source did not provide.
    df = ensure_optional_columns(df)

    df["validation_errors"] = ""

    # =====================================================
    # TRANSACTION ID
    # =====================================================

    missing_id = (
        df["transaction_id"].isna()
        | (
            df["transaction_id"]
            .astype(str)
            .str.strip()
            == ""
        )
    )

    df.loc[
        missing_id,
        "validation_errors",
    ] += "Missing transaction_id; "

    duplicate_id = (
        df["transaction_id"]
        .duplicated(
            keep=False
        )
    )

    df.loc[
        duplicate_id,
        "validation_errors",
    ] += "Duplicate transaction_id; "

    # =====================================================
    # DATE
    # =====================================================

    parsed_dates = pd.to_datetime(
        df["date"],
        errors="coerce",
    )

    invalid_date = parsed_dates.isna()

    df.loc[
        invalid_date,
        "validation_errors",
    ] += "Invalid date; "

    df["date"] = parsed_dates

    # =====================================================
    # AMOUNT
    # =====================================================

    numeric_amount = pd.to_numeric(
        df["amount"],
        errors="coerce",
    )

    invalid_amount = (
        numeric_amount.isna()
        | (numeric_amount <= 0)
    )

    df.loc[
        invalid_amount,
        "validation_errors",
    ] += "Invalid amount; "

    df["amount"] = numeric_amount

    # =====================================================
    # CURRENCY
    # =====================================================

    df["currency"] = (
        df["currency"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    invalid_currency = (
        ~df["currency"]
        .isin(ALLOWED_CURRENCIES)
    )

    df.loc[
        invalid_currency,
        "validation_errors",
    ] += "Invalid currency; "

    # =====================================================
    # OPTIONAL TEXT FIELDS
    # =====================================================

    for column in [
        "description",
        "vendor",
        "category",
        "department",
    ]:

        df[column] = (
            df[column]
            .where(
                df[column].notna(),
                None,
            )
        )

        if df[column].notna().any():

            df.loc[
                df[column].notna(),
                column,
            ] = (
                df.loc[
                    df[column].notna(),
                    column,
                ]
                .astype(str)
                .str.strip()
            )

            blank_mask = (
                df[column].notna()
                & (df[column] == "")
            )

            df.loc[
                blank_mask,
                column,
            ] = None

    # =====================================================
    # OPTIONAL TRANSACTION TYPE
    # =====================================================

    transaction_type_present = (
        df["transaction_type"]
        .notna()
    )

    df.loc[
        transaction_type_present,
        "transaction_type",
    ] = (
        df.loc[
            transaction_type_present,
            "transaction_type",
        ]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    invalid_type = (
        transaction_type_present
        & ~df["transaction_type"]
        .isin(ALLOWED_TRANSACTION_TYPES)
    )

    df.loc[
        invalid_type,
        "validation_errors",
    ] += "Invalid transaction_type; "

    # =====================================================
    # SPLIT VALID / INVALID
    # =====================================================

    valid_mask = (
        df["validation_errors"] == ""
    )

    valid_df = (
        df.loc[
            valid_mask
        ]
        .copy()
    )

    invalid_df = (
        df.loc[
            ~valid_mask
        ]
        .copy()
    )

    return valid_df, invalid_df