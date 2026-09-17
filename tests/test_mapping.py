import pandas as pd
import pytest

from src.mapping import (
    apply_column_mapping,
    get_mapping_summary,
    normalize_column_name,
    suggest_column_mapping,
    validate_mapping,
)


def test_normalize_column_name():
    assert (
        normalize_column_name(
            " Posting_Date "
        )
        == "posting date"
    )


def test_suggest_column_mapping():
    source_columns = [
        "Document Number",
        "Posting Date",
        "Supplier",
        "Gross Amount",
        "Currency",
    ]

    mapping = suggest_column_mapping(
        source_columns
    )

    assert mapping == {
        "Document Number": (
            "transaction_id"
        ),
        "Posting Date": "date",
        "Supplier": "vendor",
        "Gross Amount": "amount",
        "Currency": "currency",
    }


def test_apply_column_mapping():
    df = pd.DataFrame(
        [
            {
                "Document Number": "1001",
                "Posting Date": "2026-09-01",
                "Supplier": "AWS",
                "Gross Amount": 15000,
                "Currency": "SGD",
            }
        ]
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

    mapped_df = apply_column_mapping(
        df,
        mapping,
    )

    assert (
        mapped_df.loc[
            0,
            "transaction_id",
        ]
        == "1001"
    )

    assert (
        mapped_df.loc[
            0,
            "vendor",
        ]
        == "AWS"
    )

    assert (
        mapped_df.loc[
            0,
            "amount",
        ]
        == 15000
    )


def test_unmapped_columns_are_preserved():
    df = pd.DataFrame(
        [
            {
                "Document Number": "1001",
                "Posting Date": "2026-09-01",
                "Supplier": "AWS",
                "Gross Amount": 15000,
                "Currency": "SGD",
                "Custom Field": "ABC",
            }
        ]
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

    mapped_df = apply_column_mapping(
        df,
        mapping,
    )

    assert "Custom Field" in mapped_df.columns

    assert (
        mapped_df.loc[
            0,
            "Custom Field",
        ]
        == "ABC"
    )


def test_invalid_source_column_rejected():
    df = pd.DataFrame(
        {
            "Amount": [100],
        }
    )

    mapping = {
        "Does Not Exist": "amount",
    }

    with pytest.raises(
        ValueError
    ):
        validate_mapping(
            mapping,
            list(df.columns),
        )


def test_invalid_canonical_field_rejected():
    df = pd.DataFrame(
        {
            "Amount": [100],
        }
    )

    mapping = {
        "Amount": "random_field",
    }

    with pytest.raises(
        ValueError
    ):
        validate_mapping(
            mapping,
            list(df.columns),
        )


def test_duplicate_canonical_mapping_rejected():
    df = pd.DataFrame(
        {
            "Gross Amount": [100],
            "Net Amount": [90],
        }
    )

    mapping = {
        "Gross Amount": "amount",
        "Net Amount": "amount",
    }

    with pytest.raises(
        ValueError
    ):
        validate_mapping(
            mapping,
            list(df.columns),
        )


def test_mapping_summary():
    df = pd.DataFrame(
        {
            "Document Number": ["1001"],
            "Posting Date": [
                "2026-09-01"
            ],
            "Gross Amount": [100],
        }
    )

    mapping = {
        "Document Number": (
            "transaction_id"
        ),
        "Posting Date": "date",
        "Gross Amount": "amount",
    }

    summary = get_mapping_summary(
        df,
        mapping,
    )

    assert (
        "transaction_id"
        in summary[
            "available_canonical_fields"
        ]
    )

    assert (
        "currency"
        in summary[
            "missing_canonical_fields"
        ]
    )
    