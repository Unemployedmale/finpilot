from __future__ import annotations

import pandas as pd


REQUIRED_COLUMNS = [
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

ALLOWED_TRANSACTION_TYPES = {"revenue", "expense"}
ALLOWED_CURRENCIES = {"SGD", "USD", "EUR", "GBP"}


def validate_required_columns(df: pd.DataFrame) -> list[str]:
    """
    Return a list of required columns that are missing from the DataFrame.
    """
    return [column for column in REQUIRED_COLUMNS if column not in df.columns]


def validate_transactions(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Validate transaction records.

    Returns:
        valid_df:
            Rows that pass all validation rules.

        invalid_df:
            Rows that fail at least one rule, including a validation_errors column.
    """
    df = df.copy()

    missing_columns = validate_required_columns(df)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {', '.join(missing_columns)}"
        )

    df["validation_errors"] = ""

    # transaction_id
    missing_id = df["transaction_id"].isna() | (
        df["transaction_id"].astype(str).str.strip() == ""
    )
    df.loc[missing_id, "validation_errors"] += "Missing transaction_id; "

    duplicate_id = df["transaction_id"].duplicated(keep=False)
    df.loc[duplicate_id, "validation_errors"] += "Duplicate transaction_id; "

    # date
    parsed_dates = pd.to_datetime(df["date"], errors="coerce")
    invalid_date = parsed_dates.isna()
    df.loc[invalid_date, "validation_errors"] += "Invalid date; "
    df["date"] = parsed_dates

    # description
    missing_description = df["description"].isna() | (
        df["description"].astype(str).str.strip() == ""
    )
    df.loc[missing_description, "validation_errors"] += "Missing description; "

    # vendor
    missing_vendor = df["vendor"].isna() | (
        df["vendor"].astype(str).str.strip() == ""
    )
    df.loc[missing_vendor, "validation_errors"] += "Missing vendor; "

    # amount
    numeric_amount = pd.to_numeric(df["amount"], errors="coerce")
    invalid_amount = numeric_amount.isna() | (numeric_amount <= 0)
    df.loc[invalid_amount, "validation_errors"] += "Invalid amount; "
    df["amount"] = numeric_amount

    # transaction_type
    df["transaction_type"] = (
        df["transaction_type"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    invalid_type = ~df["transaction_type"].isin(ALLOWED_TRANSACTION_TYPES)
    df.loc[invalid_type, "validation_errors"] += "Invalid transaction_type; "

    # category
    missing_category = df["category"].isna() | (
        df["category"].astype(str).str.strip() == ""
    )
    df.loc[missing_category, "validation_errors"] += "Missing category; "

    # department
    missing_department = df["department"].isna() | (
        df["department"].astype(str).str.strip() == ""
    )
    df.loc[missing_department, "validation_errors"] += "Missing department; "

    # currency
    df["currency"] = (
        df["currency"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    invalid_currency = ~df["currency"].isin(ALLOWED_CURRENCIES)
    df.loc[invalid_currency, "validation_errors"] += "Invalid currency; "

    valid_mask = df["validation_errors"] == ""

    valid_df = df.loc[valid_mask].copy()
    invalid_df = df.loc[~valid_mask].copy()

    return valid_df, invalid_df