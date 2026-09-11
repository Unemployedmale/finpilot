from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def load_file(file_path: Path) -> pd.DataFrame:
    """
    Load a CSV or Excel financial transaction file.

    This function only reads the file.
    It does not modify the source data.
    """

    suffix = file_path.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(
            file_path,
            low_memory=False,
        )

    if suffix in {".xlsx", ".xls"}:
        try:
            return pd.read_excel(
                file_path
            )

        except ImportError as exc:
            raise RuntimeError(
                "Excel support requires openpyxl. "
                "Install it with: pip install openpyxl"
            ) from exc

    raise ValueError(
        f"Unsupported file type: {suffix}. "
        "Use CSV, XLSX or XLS."
    )


def profile_dataframe(
    df: pd.DataFrame,
    show_sample: bool = False,
) -> None:
    """
    Print a structural profile of a financial dataset.

    The goal is to understand the data before attempting
    to map it into FinPilot's trusted transaction schema.
    """

    print()
    print("=" * 70)
    print("FINPILOT REAL-DATA PROFILE")
    print("=" * 70)

    # =====================================================
    # BASIC DATASET INFORMATION
    # =====================================================

    print()
    print("1. DATASET SIZE")
    print("-" * 70)

    print(f"Rows:    {len(df):,}")
    print(f"Columns: {len(df.columns):,}")

    # =====================================================
    # COLUMN NAMES
    # =====================================================

    print()
    print("2. COLUMNS")
    print("-" * 70)

    for index, column in enumerate(
        df.columns,
        start=1,
    ):
        print(
            f"{index:>2}. {column}"
        )

    # =====================================================
    # DATA TYPES
    # =====================================================

    print()
    print("3. DATA TYPES")
    print("-" * 70)

    for column in df.columns:
        print(
            f"{column}: {df[column].dtype}"
        )

    # =====================================================
    # MISSING VALUES
    # =====================================================

    print()
    print("4. MISSING VALUES")
    print("-" * 70)

    missing_count = (
        df.isna()
        .sum()
    )

    missing_percentage = (
        df.isna()
        .mean()
        .mul(100)
    )

    missing_report = pd.DataFrame(
        {
            "missing_count": missing_count,
            "missing_percent": (
                missing_percentage
            ),
        }
    )

    missing_report[
        "missing_percent"
    ] = missing_report[
        "missing_percent"
    ].round(2)

    print(
        missing_report.to_string()
    )

    # =====================================================
    # UNIQUE VALUES
    # =====================================================

    print()
    print("5. UNIQUE VALUES PER COLUMN")
    print("-" * 70)

    for column in df.columns:

        unique_count = (
            df[column]
            .nunique(
                dropna=True
            )
        )

        print(
            f"{column}: "
            f"{unique_count:,}"
        )

    # =====================================================
    # EXACT DUPLICATE ROWS
    # =====================================================

    print()
    print("6. EXACT DUPLICATE ROWS")
    print("-" * 70)

    duplicate_count = (
        df.duplicated(
            keep=False
        )
        .sum()
    )

    print(
        f"Rows belonging to exact duplicate groups: "
        f"{duplicate_count:,}"
    )

    # =====================================================
    # EMPTY DATASET CHECK
    # =====================================================

    print()
    print("7. EMPTY DATASET CHECK")
    print("-" * 70)

    if df.empty:
        print(
            "WARNING: Dataset contains no rows."
        )
    else:
        print(
            "Dataset contains transaction rows."
        )

    # =====================================================
    # OPTIONAL SAMPLE
    # =====================================================

    if show_sample:

        print()
        print("8. SAMPLE ROWS")
        print("-" * 70)

        print(
            df.head(5).to_string(
                index=False
            )
        )

    else:

        print()
        print("8. SAMPLE ROWS")
        print("-" * 70)

        print(
            "Hidden by default to reduce accidental "
            "exposure of sensitive financial data."
        )

        print(
            "Use --show-sample if you intentionally "
            "want to display the first five rows."
        )

    # =====================================================
    # FINPILOT TARGET SCHEMA
    # =====================================================

    print()
    print("9. FINPILOT TARGET SCHEMA")
    print("-" * 70)

    required_columns = [
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

    existing_columns = {
        str(column).strip().lower()
        for column in df.columns
    }

    matched_columns = []
    missing_columns = []

    for required_column in required_columns:

        if required_column in existing_columns:
            matched_columns.append(
                required_column
            )
        else:
            missing_columns.append(
                required_column
            )

    print()
    print("Directly matching columns:")

    if matched_columns:
        for column in matched_columns:
            print(
                f"  ✓ {column}"
            )
    else:
        print(
            "  None"
        )

    print()
    print("FinPilot columns not directly found:")

    if missing_columns:
        for column in missing_columns:
            print(
                f"  - {column}"
            )
    else:
        print(
            "  None"
        )

    print()
    print("=" * 70)
    print("PROFILE COMPLETE")
    print("=" * 70)
    print()


def main() -> None:
    """
    Command-line entry point.
    """

    parser = argparse.ArgumentParser(
        description=(
            "Profile a real financial transaction "
            "file before FinPilot ingestion."
        )
    )

    parser.add_argument(
        "file",
        type=Path,
        help=(
            "Path to CSV or Excel transaction file."
        ),
    )

    parser.add_argument(
        "--show-sample",
        action="store_true",
        help=(
            "Display the first five rows."
        ),
    )

    args = parser.parse_args()

    file_path = args.file

    if not file_path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    print()
    print(
        f"Loading: {file_path}"
    )

    df = load_file(
        file_path
    )

    profile_dataframe(
        df,
        show_sample=args.show_sample,
    )


if __name__ == "__main__":
    main()