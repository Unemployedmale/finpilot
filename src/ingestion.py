from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

import pandas as pd


SUPPORTED_FILE_TYPES = {
    ".csv",
    ".xlsx",
}


def load_csv(
    source: str | Path | BinaryIO,
) -> pd.DataFrame:
    """
    Load a CSV file into a Pandas DataFrame.
    """

    return pd.read_csv(
        source,
        low_memory=False,
    )


def load_excel(
    source: str | Path | BinaryIO,
) -> pd.DataFrame:
    """
    Load an Excel workbook into a Pandas DataFrame.

    V1 reads the first worksheet.
    """

    return pd.read_excel(
        source,
        sheet_name=0,
    )


def load_financial_file(
    source: str | Path | BinaryIO,
    filename: str | None = None,
) -> pd.DataFrame:
    """
    Load a supported financial file.

    Supports:
    - CSV
    - XLSX

    Parameters
    ----------
    source:
        File path or file-like object.

    filename:
        Required when source is a file-like object,
        because FinPilot needs the extension to determine
        which reader to use.

    Returns
    -------
    pd.DataFrame
    """

    if filename is not None:
        suffix = Path(
            filename
        ).suffix.lower()

    elif isinstance(
        source,
        (str, Path),
    ):
        suffix = Path(
            source
        ).suffix.lower()

    else:
        raise ValueError(
            "filename is required when source "
            "is a file-like object."
        )

    if suffix not in SUPPORTED_FILE_TYPES:
        raise ValueError(
            "Unsupported file type: "
            f"{suffix}. "
            "FinPilot V1 supports CSV and XLSX."
        )

    if suffix == ".csv":
        df = load_csv(
            source
        )

    else:
        df = load_excel(
            source
        )

    if df.empty:
        raise ValueError(
            "Uploaded file contains no rows."
        )

    return df
