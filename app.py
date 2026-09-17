from __future__ import annotations

from collections import Counter

import pandas as pd
import streamlit as st

from src.database import DB_PATH, initialize_database
from src.ingestion import load_financial_file
from src.mapping import (
    apply_column_mapping,
    suggest_column_mapping,
)
from src.pipeline import process_financial_file
from src.review import (
    clear_review_database,
    get_dashboard_metrics,
    get_exception_queue,
    get_exception_signals,
    update_exception_status,
)
from src.schema import (
    CANONICAL_FIELDS,
    CORE_REQUIRED_FIELDS,
)


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="FinPilot",
    page_icon="📊",
    layout="wide",
)


initialize_database(DB_PATH)


# =========================================================
# SESSION STATE
# =========================================================

if "processing_result" not in st.session_state:
    st.session_state.processing_result = None


# =========================================================
# HEADER
# =========================================================

st.title("FinPilot")

st.caption(
    "Financial Exception Intelligence — "
    "turn transaction data into a prioritized "
    "human-review workflow."
)


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.header("FinPilot V1")

    st.write(
        "Upload transaction data, map the source "
        "fields, run deterministic controls and "
        "review financial exceptions."
    )

    st.divider()

    st.subheader("Current Controls")

    st.write("• High Value")
    st.write("• Duplicate Candidate")

    st.divider()

    if st.button(
        "Reset Demo Database",
        use_container_width=True,
    ):

        clear_review_database(
            DB_PATH
        )

        st.session_state.processing_result = None

        st.success(
            "Demo database cleared."
        )

        st.rerun()


# =========================================================
# MAIN NAVIGATION
# =========================================================

upload_tab, review_tab = st.tabs(
    [
        "Upload & Process",
        "Exception Review",
    ]
)


# =========================================================
# TAB 1 — UPLOAD + PROCESS
# =========================================================

with upload_tab:

    st.subheader(
        "1. Upload Financial Data"
    )

    uploaded_file = st.file_uploader(
        "Upload a CSV or XLSX transaction file",
        type=[
            "csv",
            "xlsx",
        ],
    )

    if uploaded_file is None:

        st.info(
            "Upload a transaction file to begin."
        )

    else:

        try:

            raw_df = load_financial_file(
                uploaded_file,
                filename=uploaded_file.name,
            )

        except Exception as exc:

            st.error(
                f"Could not load file: {exc}"
            )

            st.stop()

        st.success(
            f"Loaded {len(raw_df):,} rows "
            f"and {len(raw_df.columns)} columns."
        )

        with st.expander(
            "Preview Source Data",
            expanded=False,
        ):

            st.dataframe(
                raw_df.head(25),
                use_container_width=True,
            )

        # =================================================
        # COLUMN MAPPING
        # =================================================

        st.subheader(
            "2. Confirm Column Mapping"
        )

        suggested_mapping = (
            suggest_column_mapping(
                list(raw_df.columns)
            )
        )

        reverse_suggestions = {
            canonical: source
            for source, canonical
            in suggested_mapping.items()
        }

        mapping = {}

        mapping_columns = st.columns(
            3
        )

        canonical_options = [
            "— Not mapped —"
        ] + list(raw_df.columns)

        for index, canonical_field in enumerate(
            CANONICAL_FIELDS
        ):

            container = mapping_columns[
                index % 3
            ]

            suggested_source = (
                reverse_suggestions.get(
                    canonical_field
                )
            )

            if (
                suggested_source
                in canonical_options
            ):
                default_index = (
                    canonical_options.index(
                        suggested_source
                    )
                )
            else:
                default_index = 0

            label = canonical_field

            if (
                canonical_field
                in CORE_REQUIRED_FIELDS
            ):
                label += " *"

            selected_source = (
                container.selectbox(
                    label,
                    options=canonical_options,
                    index=default_index,
                    key=(
                        f"mapping_"
                        f"{canonical_field}"
                    ),
                )
            )

            if (
                selected_source
                != "— Not mapped —"
            ):

                mapping[
                    selected_source
                ] = canonical_field

        mapped_targets = list(
            mapping.values()
        )

        duplicate_targets = [
            field
            for field, count
            in Counter(
                mapped_targets
            ).items()
            if count > 1
        ]

        missing_required = [
            field
            for field
            in CORE_REQUIRED_FIELDS
            if field
            not in mapped_targets
        ]

        if duplicate_targets:

            st.error(
                "A canonical field has been "
                "mapped more than once: "
                + ", ".join(
                    duplicate_targets
                )
            )

        if missing_required:

            st.warning(
                "Required mappings missing: "
                + ", ".join(
                    missing_required
                )
            )

        # =================================================
        # MAPPING PREVIEW
        # =================================================

        if (
            mapping
            and not duplicate_targets
        ):

            try:

                mapped_preview = (
                    apply_column_mapping(
                        raw_df.head(10),
                        mapping,
                    )
                )

                with st.expander(
                    "Preview Mapped Data",
                    expanded=False,
                ):

                    st.dataframe(
                        mapped_preview,
                        use_container_width=True,
                    )

            except Exception as exc:

                st.error(
                    f"Mapping error: {exc}"
                )

        # =================================================
        # THRESHOLD
        # =================================================

        st.subheader(
            "3. Configure Controls"
        )

        st.write(
            "V1 high-value thresholds are "
            "configurable by currency."
        )

        threshold_columns = (
            st.columns(4)
        )

        sgd_threshold = (
            threshold_columns[0]
            .number_input(
                "SGD",
                min_value=0.0,
                value=10000.0,
                step=1000.0,
            )
        )

        usd_threshold = (
            threshold_columns[1]
            .number_input(
                "USD",
                min_value=0.0,
                value=10000.0,
                step=1000.0,
            )
        )

        eur_threshold = (
            threshold_columns[2]
            .number_input(
                "EUR",
                min_value=0.0,
                value=10000.0,
                step=1000.0,
            )
        )

        gbp_threshold = (
            threshold_columns[3]
            .number_input(
                "GBP",
                min_value=0.0,
                value=10000.0,
                step=1000.0,
            )
        )

        thresholds = {
            "SGD": sgd_threshold,
            "USD": usd_threshold,
            "EUR": eur_threshold,
            "GBP": gbp_threshold,
        }

        # =================================================
        # PROCESS BUTTON
        # =================================================

        st.subheader(
            "4. Process Transactions"
        )

        processing_disabled = bool(
            missing_required
            or duplicate_targets
        )

        if st.button(
            "Run FinPilot Analysis",
            type="primary",
            disabled=processing_disabled,
            use_container_width=True,
        ):

            try:

                uploaded_file.seek(0)

                result = (
                    process_financial_file(
                        uploaded_file,
                        mapping=mapping,
                        filename=(
                            uploaded_file.name
                        ),
                        db_path=DB_PATH,
                        high_value_thresholds=(
                            thresholds
                        ),
                    )
                )

                st.session_state[
                    "processing_result"
                ] = result

                st.success(
                    "FinPilot analysis completed."
                )

            except Exception as exc:

                st.error(
                    "Processing failed: "
                    f"{exc}"
                )

        # =================================================
        # RESULTS
        # =================================================

        result = st.session_state.get(
            "processing_result"
        )

        if result is not None:

            st.divider()

            st.subheader(
                "Processing Results"
            )

            result_columns = (
                st.columns(5)
            )

            result_columns[0].metric(
                "Source Rows",
                result["raw_rows"],
            )

            result_columns[1].metric(
                "Valid",
                result["valid_rows"],
            )

            result_columns[2].metric(
                "Invalid",
                result["invalid_rows"],
            )

            result_columns[3].metric(
                "Signals",
                result[
                    "signals_generated"
                ],
            )

            result_columns[4].metric(
                "Exceptions",
                result[
                    "exceptions_created"
                ],
            )

            signal_counts = (
                result[
                    "signal_counts"
                ]
            )

            if signal_counts:

                st.subheader(
                    "Detected Signals"
                )

                signal_df = pd.DataFrame(
                    [
                        {
                            "Signal Type": (
                                signal_type
                            ),
                            "Count": count,
                        }
                        for (
                            signal_type,
                            count,
                        )
                        in signal_counts.items()
                    ]
                )

                st.dataframe(
                    signal_df,
                    use_container_width=True,
                    hide_index=True,
                )

            if (
                result[
                    "invalid_rows"
                ]
                > 0
            ):

                with st.expander(
                    "Invalid Transactions",
                    expanded=False,
                ):

                    st.dataframe(
                        result[
                            "invalid_df"
                        ],
                        use_container_width=True,
                    )

            st.info(
                "Open the Exception Review tab "
                "to investigate flagged transactions."
            )


# =========================================================
# TAB 2 — EXCEPTION REVIEW
# =========================================================

with review_tab:

    st.subheader(
        "Exception Review"
    )

    metrics = get_dashboard_metrics(
        DB_PATH
    )

    metric_columns = st.columns(
        4
    )

    metric_columns[0].metric(
        "Transactions",
        metrics[
            "transactions"
        ],
    )

    metric_columns[1].metric(
        "Exceptions",
        metrics[
            "exceptions"
        ],
    )

    metric_columns[2].metric(
        "Open",
        metrics[
            "open_exceptions"
        ],
    )

    metric_columns[3].metric(
        "High Priority",
        metrics[
            "high_priority"
        ],
    )

    st.divider()

    queue_df = (
        get_exception_queue(
            DB_PATH
        )
    )

    if queue_df.empty:

        st.info(
            "No exceptions available. "
            "Process a transaction file first."
        )

    else:

        # =================================================
        # FILTERS
        # =================================================

        filter_columns = (
            st.columns(2)
        )

        status_options = [
            "ALL"
        ] + sorted(
            queue_df[
                "status"
            ]
            .dropna()
            .unique()
            .tolist()
        )

        priority_options = [
            "ALL"
        ] + sorted(
            queue_df[
                "priority"
            ]
            .dropna()
            .unique()
            .tolist()
        )

        status_filter = (
            filter_columns[0]
            .selectbox(
                "Status",
                status_options,
            )
        )

        priority_filter = (
            filter_columns[1]
            .selectbox(
                "Priority",
                priority_options,
            )
        )

        filtered_df = (
            queue_df.copy()
        )

        if status_filter != "ALL":

            filtered_df = (
                filtered_df[
                    filtered_df[
                        "status"
                    ]
                    == status_filter
                ]
            )

        if priority_filter != "ALL":

            filtered_df = (
                filtered_df[
                    filtered_df[
                        "priority"
                    ]
                    == priority_filter
                ]
            )

        # =================================================
        # REVIEW QUEUE
        # =================================================

        st.subheader(
            "Review Queue"
        )

        display_columns = [
            "exception_id",
            "priority",
            "status",
            "transaction_id",
            "date",
            "vendor",
            "amount",
            "currency",
            "signal_types",
            "signal_count",
        ]

        st.dataframe(
            filtered_df[
                display_columns
            ],
            use_container_width=True,
            hide_index=True,
        )

        if filtered_df.empty:

            st.warning(
                "No exceptions match "
                "the selected filters."
            )

        else:

            # =============================================
            # EXCEPTION SELECTOR
            # =============================================

            st.subheader(
                "Exception Detail"
            )

            exception_ids = (
                filtered_df[
                    "exception_id"
                ]
                .tolist()
            )

            selected_exception_id = (
                st.selectbox(
                    "Select exception",
                    exception_ids,
                )
            )

            selected_row = (
                queue_df[
                    queue_df[
                        "exception_id"
                    ]
                    == selected_exception_id
                ]
                .iloc[0]
            )

            detail_columns = (
                st.columns(3)
            )

            detail_columns[0].write(
                "**Transaction ID**"
            )

            detail_columns[0].write(
                selected_row[
                    "transaction_id"
                ]
            )

            detail_columns[1].write(
                "**Priority**"
            )

            detail_columns[1].write(
                selected_row[
                    "priority"
                ]
            )

            detail_columns[2].write(
                "**Status**"
            )

            detail_columns[2].write(
                selected_row[
                    "status"
                ]
            )

            st.write(
                "**Vendor:**",
                selected_row[
                    "vendor"
                ],
            )

            st.write(
                "**Amount:**",
                (
                    f"{selected_row['currency']} "
                    f"{selected_row['amount']:,.2f}"
                ),
            )

            st.write(
                "**Date:**",
                selected_row[
                    "date"
                ],
            )

            if pd.notna(
                selected_row[
                    "description"
                ]
            ):

                st.write(
                    "**Description:**",
                    selected_row[
                        "description"
                    ],
                )

            # =============================================
            # SIGNAL EVIDENCE
            # =============================================

            signals = (
                get_exception_signals(
                    selected_exception_id,
                    DB_PATH,
                )
            )

            st.write(
                "### Supporting Evidence"
            )

            for signal in signals:

                with st.expander(
                    (
                        f"{signal['signal_type']} "
                        f"— {signal['severity']}"
                    ),
                    expanded=True,
                ):

                    st.write(
                        signal[
                            "reason"
                        ]
                    )

                    st.write(
                        "**Source:**",
                        signal[
                            "source"
                        ],
                    )

                    if (
                        signal[
                            "score"
                        ]
                        is not None
                    ):

                        st.write(
                            "**Score:**",
                            signal[
                                "score"
                            ],
                        )

                    st.json(
                        signal[
                            "evidence"
                        ]
                    )

            # =============================================
            # HUMAN REVIEW STATUS
            # =============================================

            st.write(
                "### Human Review"
            )

            status_choices = [
                "OPEN",
                "NEEDS_INFO",
                "CLEARED",
                "CONFIRMED_ISSUE",
            ]

            current_status = (
                selected_row[
                    "status"
                ]
            )

            status_index = (
                status_choices.index(
                    current_status
                )
            )

            new_status = (
                st.selectbox(
                    "Review decision",
                    status_choices,
                    index=status_index,
                    key=(
                        "status_"
                        f"{selected_exception_id}"
                    ),
                )
            )

            if st.button(
                "Update Review Status",
                type="primary",
            ):

                update_exception_status(
                    selected_exception_id,
                    new_status,
                    DB_PATH,
                )

                st.success(
                    "Review status updated."
                )

                st.rerun()