from __future__ import annotations


# =========================================================
# FINPILOT CANONICAL TRANSACTION SCHEMA
# =========================================================

# These fields are required for a transaction to enter
# FinPilot's trusted transaction layer.
#
# They represent the minimum information needed to identify
# a transaction and interpret its monetary value safely.

CORE_REQUIRED_FIELDS = [
    "transaction_id",
    "date",
    "amount",
    "currency",
]


# These fields are useful, but a transaction should not be
# rejected simply because the source system does not provide
# them.
#
# Individual controls may require some of these fields.

OPTIONAL_FIELDS = [
    "description",
    "vendor",
    "transaction_type",
    "category",
    "department",
]


CANONICAL_FIELDS = (
    CORE_REQUIRED_FIELDS
    + OPTIONAL_FIELDS
)


# =========================================================
# SUPPORTED VALUES
# =========================================================

ALLOWED_TRANSACTION_TYPES = {
    "revenue",
    "expense",
}


ALLOWED_CURRENCIES = {
    "SGD",
    "USD",
    "EUR",
    "GBP",
}


# =========================================================
# FIELD ALIASES
# =========================================================

# These provide simple deterministic mapping suggestions.
#
# Example:
#
# "Posting Date"
#       ↓
# "date"
#
# The user will eventually confirm suggested mappings in
# the Streamlit upload interface.

FIELD_ALIASES = {
    "transaction_id": {
        "transaction_id",
        "transaction id",
        "transaction number",
        "transaction no",
        "txn_id",
        "txn id",
        "document number",
        "document no",
        "reference",
        "reference number",
        "payment_id",
        "payment id",
    },

    "date": {
        "date",
        "transaction_date",
        "transaction date",
        "posting_date",
        "posting date",
        "payment_date",
        "payment date",
        "document date",
    },

    "description": {
        "description",
        "transaction description",
        "narration",
        "details",
        "memo",
        "remarks",
    },

    "vendor": {
        "vendor",
        "vendor_name",
        "vendor name",
        "supplier",
        "supplier_name",
        "supplier name",
        "merchant",
        "merchant name",
        "counterparty",
        "counterparty name",
        "customer",
        "customer name",
    },

    "amount": {
        "amount",
        "transaction amount",
        "payment amount",
        "gross amount",
        "local amount",
        "invoice amount",
        "amount_inr",
        "amount_sgd",
    },

    "transaction_type": {
        "transaction_type",
        "transaction type",
        "type",
        "payment category",
        "payment_category",
    },

    "category": {
        "category",
        "expense category",
        "payment category",
        "payment_category",
        "gl account name",
        "gl_account_name",
    },

    "department": {
        "department",
        "cost center",
        "cost centre",
        "cost_center",
        "business unit",
        "business_unit",
        "division",
    },

    "currency": {
        "currency",
        "currency code",
        "currency_code",
        "curr",
        "ccy",
    },
}