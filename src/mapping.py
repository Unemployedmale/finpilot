from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from src.schema import (
    CANONICAL_FIELDS,
    FIELD_ALIASES,
)


def normalize_column_name(
    column_name: str,
) -> str:
    """
    Normalize a source column name for matching.

    Example:
        "Posting Date"
        "posting_date"
        "POSTING DATE"

    all become a comparable normalized form.
    """

    normalized = (
        str(column_name)
        .strip()
        .lower()
        .replace("_", " ")
        .replace("-", " ")
    )

    normalized = " ".join(
        normalized.split()
    )

    return normalized


def suggest_column_mapping(
    source_columns: list[str],
) -> dict[str, str]:
    """
    Suggest source-column mappings into FinPilot's
    canonical schema using deterministic aliases.

    Returns
    -------
    dict

    Example:
        {
            "Document Number": "transaction_id",
            "Posting Date": "date",
            "Supplier": "vendor",
            "Gross Amount": "amount",
            "Currency": "currency",
        }
    """

    suggestions: dict[str, str] = {}

    normalized_aliases: dict[
        str,
        set[str],
    ] = {}

    for canonical_field, aliases in (
        FIELD_ALIASES.items()
    ):

        normalized_aliases[
            canonical_field
        ] = {
            normalize_column_name(alias)
            for alias in aliases
        }

    used_canonical_fields: set[str] = set()

    for source_column in source_columns:

        normalized_source = (
            normalize_column_name(
                source_column
            )
        )

        for (
            canonical_field,
            aliases,
        ) in normalized_aliases.items():

            if (
                canonical_field
                in used_canonical_fields
            ):
                continue

            if normalized_source in aliases:

                suggestions[
                    source_column
                ] = canonical_field

                used_canonical_fields.add(
                    canonical_field
                )

                break

    return suggestions


def validate_mapping(
    mapping: Mapping[str, str],
    source_columns: list[str],
) -> None:
    """
    Validate a user-confirmed source-to-canonical mapping.

    Raises ValueError if:

    - source column does not exist
    - canonical field is invalid
    - multiple source columns map to the same canonical field
    """

    source_column_set = set(
        source_columns
    )

    canonical_targets: list[str] = []

    for (
        source_column,
        canonical_field,
    ) in mapping.items():

        if (
            source_column
            not in source_column_set
        ):
            raise ValueError(
                "Mapping references missing "
                f"source column: "
                f"{source_column}"
            )

        if (
            canonical_field
            not in CANONICAL_FIELDS
        ):
            raise ValueError(
                "Invalid FinPilot canonical "
                f"field: {canonical_field}"
            )

        canonical_targets.append(
            canonical_field
        )

    if (
        len(canonical_targets)
        != len(set(canonical_targets))
    ):
        raise ValueError(
            "Multiple source columns cannot "
            "map to the same canonical field."
        )


def apply_column_mapping(
    df: pd.DataFrame,
    mapping: Mapping[str, str],
) -> pd.DataFrame:
    """
    Convert source-system columns into FinPilot's
    canonical transaction schema.

    Unmapped source columns are preserved in the returned
    DataFrame so that raw source information is not lost
    during ingestion.

    Parameters
    ----------
    df:
        Raw source DataFrame.

    mapping:
        Dictionary where:

        key   = source column
        value = FinPilot canonical field

    Returns
    -------
    pd.DataFrame
        DataFrame with canonical column names.
    """

    validate_mapping(
        mapping,
        source_columns=list(df.columns),
    )

    mapped_df = df.copy()

    mapped_df = mapped_df.rename(
        columns=dict(mapping)
    )

    return mapped_df


def get_mapping_summary(
    df: pd.DataFrame,
    mapping: Mapping[str, str],
) -> dict[str, Any]:
    """
    Return a simple mapping summary for future UI use.
    """

    mapped_fields = set(
        mapping.values()
    )

    available_canonical_fields = [
        field
        for field in CANONICAL_FIELDS
        if field in mapped_fields
    ]

    missing_canonical_fields = [
        field
        for field in CANONICAL_FIELDS
        if field not in mapped_fields
    ]

    unmapped_source_columns = [
        column
        for column in df.columns
        if column not in mapping
    ]

    return {
        "source_columns": list(
            df.columns
        ),
        "mapping": dict(mapping),
        "available_canonical_fields": (
            available_canonical_fields
        ),
        "missing_canonical_fields": (
            missing_canonical_fields
        ),
        "unmapped_source_columns": (
            unmapped_source_columns
        ),
    }