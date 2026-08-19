import pandas as pd
import pytest

from src.validation import validate_transactions


def test_clean_transactions_are_valid():
    """All rows in the clean sample dataset should pass validation."""

    df = pd.read_csv("data/sample_transactions.csv")

    valid_df, invalid_df = validate_transactions(df)

    assert len(valid_df) == 10
    assert len(invalid_df) == 0


def test_invalid_date_is_rejected():
    """A transaction containing an invalid date should be rejected."""

    df = pd.DataFrame(
        {
            "transaction_id": ["T2001"],
            "date": ["not-a-date"],
            "description": ["AWS Cloud Services"],
            "vendor": ["AWS"],
            "amount": [1250.00],
            "transaction_type": ["expense"],
            "category": ["Technology"],
            "department": ["Engineering"],
            "currency": ["SGD"],
        }
    )

    valid_df, invalid_df = validate_transactions(df)

    assert len(valid_df) == 0
    assert len(invalid_df) == 1
    assert "Invalid date" in invalid_df.iloc[0]["validation_errors"]


def test_negative_amount_is_rejected():
    """A transaction with a negative amount should be rejected."""

    df = pd.DataFrame(
        {
            "transaction_id": ["T2002"],
            "date": ["2026-07-01"],
            "description": ["AWS Cloud Services"],
            "vendor": ["AWS"],
            "amount": [-1250.00],
            "transaction_type": ["expense"],
            "category": ["Technology"],
            "department": ["Engineering"],
            "currency": ["SGD"],
        }
    )

    valid_df, invalid_df = validate_transactions(df)

    assert len(valid_df) == 0
    assert "Invalid amount" in invalid_df.iloc[0]["validation_errors"]


def test_duplicate_transaction_ids_are_rejected():
    """Every occurrence of a duplicated transaction ID should be rejected."""

    df = pd.DataFrame(
        {
            "transaction_id": ["T2003", "T2003"],
            "date": ["2026-07-01", "2026-07-02"],
            "description": ["AWS Payment", "AWS Payment"],
            "vendor": ["AWS", "AWS"],
            "amount": [1000.00, 1000.00],
            "transaction_type": ["expense", "expense"],
            "category": ["Technology", "Technology"],
            "department": ["Engineering", "Engineering"],
            "currency": ["SGD", "SGD"],
        }
    )

    valid_df, invalid_df = validate_transactions(df)

    assert len(valid_df) == 0
    assert len(invalid_df) == 2
    assert invalid_df["validation_errors"].str.contains(
        "Duplicate transaction_id"
    ).all()


def test_missing_required_column_raises_error():
    """A file missing a required column should fail schema validation."""

    df = pd.DataFrame(
        {
            "transaction_id": ["T2004"],
            "date": ["2026-07-01"],
            "description": ["AWS Cloud Services"],
        }
    )

    with pytest.raises(ValueError, match="Missing required columns"):
        validate_transactions(df)