from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

from src.ingestion import (
    load_financial_file,
)


def test_load_csv_from_path(
    tmp_path: Path,
):
    file_path = (
        tmp_path
        / "transactions.csv"
    )

    expected_df = pd.DataFrame(
        [
            {
                "Transaction ID": "T001",
                "Amount": 1000,
            },
            {
                "Transaction ID": "T002",
                "Amount": 2000,
            },
        ]
    )

    expected_df.to_csv(
        file_path,
        index=False,
    )

    loaded_df = (
        load_financial_file(
            file_path
        )
    )

    assert len(loaded_df) == 2

    assert list(
        loaded_df.columns
    ) == [
        "Transaction ID",
        "Amount",
    ]


def test_load_xlsx_from_path(
    tmp_path: Path,
):
    file_path = (
        tmp_path
        / "transactions.xlsx"
    )

    expected_df = pd.DataFrame(
        [
            {
                "Transaction ID": "T001",
                "Amount": 1000,
            }
        ]
    )

    expected_df.to_excel(
        file_path,
        index=False,
    )

    loaded_df = (
        load_financial_file(
            file_path
        )
    )

    assert len(loaded_df) == 1

    assert (
        loaded_df.loc[
            0,
            "Transaction ID",
        ]
        == "T001"
    )


def test_load_csv_file_like_object():
    csv_bytes = BytesIO(
        (
            "Transaction ID,Amount\n"
            "T001,1000\n"
        ).encode(
            "utf-8"
        )
    )

    loaded_df = (
        load_financial_file(
            csv_bytes,
            filename=(
                "transactions.csv"
            ),
        )
    )

    assert len(loaded_df) == 1

    assert (
        loaded_df.loc[
            0,
            "Amount",
        ]
        == 1000
    )


def test_file_like_object_requires_filename():
    csv_bytes = BytesIO(
        (
            "Transaction ID,Amount\n"
            "T001,1000\n"
        ).encode(
            "utf-8"
        )
    )

    with pytest.raises(
        ValueError
    ):
        load_financial_file(
            csv_bytes
        )


def test_unsupported_file_type_rejected(
    tmp_path: Path,
):
    file_path = (
        tmp_path
        / "transactions.txt"
    )

    file_path.write_text(
        "hello"
    )

    with pytest.raises(
        ValueError
    ):
        load_financial_file(
            file_path
        )


def test_empty_csv_rejected(
    tmp_path: Path,
):
    file_path = (
        tmp_path
        / "empty.csv"
    )

    pd.DataFrame(
        columns=[
            "Transaction ID",
            "Amount",
        ]
    ).to_csv(
        file_path,
        index=False,
    )

    with pytest.raises(
        ValueError
    ):
        load_financial_file(
            file_path
        )