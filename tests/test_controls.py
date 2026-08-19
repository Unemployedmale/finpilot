import pandas as pd

from src.controls import (
    detect_duplicate_candidates,
    detect_high_value_transactions,
    run_financial_controls,
)


# =========================================================
# HIGH-VALUE CONTROL TESTS
# =========================================================

def test_high_value_transaction_is_detected():
    """
    A transaction above its configured threshold
    should produce a HIGH_VALUE signal.
    """

    df = pd.DataFrame(
        [
            {
                "transaction_id": "T0001",
                "date": "2026-08-19",
                "vendor": "AWS",
                "amount": 15000.00,
                "currency": "SGD",
            }
        ]
    )

    signals = detect_high_value_transactions(
        df,
        thresholds={"SGD": 10000.00},
    )

    assert len(signals) == 1

    signal = signals[0]

    assert signal["transaction_id"] == "T0001"
    assert signal["signal_type"] == "HIGH_VALUE"
    assert signal["source"] == "RULE"
    assert signal["severity"] == "HIGH"
    assert signal["score"] is None

    assert signal["evidence"]["amount"] == 15000.00
    assert signal["evidence"]["threshold"] == 10000.00
    assert signal["evidence"]["currency"] == "SGD"


def test_transaction_below_threshold_is_not_detected():
    """
    A transaction below the threshold should not
    generate a HIGH_VALUE signal.
    """

    df = pd.DataFrame(
        [
            {
                "transaction_id": "T0001",
                "date": "2026-08-19",
                "vendor": "AWS",
                "amount": 9000.00,
                "currency": "SGD",
            }
        ]
    )

    signals = detect_high_value_transactions(
        df,
        thresholds={"SGD": 10000.00},
    )

    assert signals == []


def test_transaction_equal_to_threshold_is_not_detected():
    """
    The current V1 rule uses:

        amount > threshold

    Therefore an amount exactly equal to the threshold
    should not generate a signal.
    """

    df = pd.DataFrame(
        [
            {
                "transaction_id": "T0001",
                "date": "2026-08-19",
                "vendor": "AWS",
                "amount": 10000.00,
                "currency": "SGD",
            }
        ]
    )

    signals = detect_high_value_transactions(
        df,
        thresholds={"SGD": 10000.00},
    )

    assert signals == []


def test_currency_without_threshold_is_skipped():
    """
    FinPilot should not invent a threshold for
    an unconfigured currency.
    """

    df = pd.DataFrame(
        [
            {
                "transaction_id": "T0001",
                "date": "2026-08-19",
                "vendor": "AWS",
                "amount": 50000.00,
                "currency": "JPY",
            }
        ]
    )

    signals = detect_high_value_transactions(
        df,
        thresholds={"SGD": 10000.00},
    )

    assert signals == []


# =========================================================
# DUPLICATE-CANDIDATE TESTS
# =========================================================

def test_duplicate_candidates_are_detected():
    """
    Different transaction IDs with the same:

    vendor
    amount
    date

    should be flagged as duplicate candidates.
    """

    df = pd.DataFrame(
        [
            {
                "transaction_id": "T0001",
                "date": "2026-08-19",
                "vendor": "AWS",
                "amount": 2500.00,
                "currency": "SGD",
            },
            {
                "transaction_id": "T0002",
                "date": "2026-08-19",
                "vendor": "AWS",
                "amount": 2500.00,
                "currency": "SGD",
            },
        ]
    )

    signals = detect_duplicate_candidates(df)

    assert len(signals) == 2

    signal_types = {
        signal["signal_type"]
        for signal in signals
    }

    transaction_ids = {
        signal["transaction_id"]
        for signal in signals
    }

    assert signal_types == {"DUPLICATE_CANDIDATE"}

    assert transaction_ids == {
        "T0001",
        "T0002",
    }


def test_duplicate_candidate_contains_other_transaction_id():
    """
    Duplicate evidence should tell the reviewer which
    other transaction matched the current transaction.
    """

    df = pd.DataFrame(
        [
            {
                "transaction_id": "T0001",
                "date": "2026-08-19",
                "vendor": "AWS",
                "amount": 2500.00,
                "currency": "SGD",
            },
            {
                "transaction_id": "T0002",
                "date": "2026-08-19",
                "vendor": "AWS",
                "amount": 2500.00,
                "currency": "SGD",
            },
        ]
    )

    signals = detect_duplicate_candidates(df)

    signal_t0001 = next(
        signal
        for signal in signals
        if signal["transaction_id"] == "T0001"
    )

    assert (
        signal_t0001["evidence"][
            "candidate_transaction_ids"
        ]
        == ["T0002"]
    )


def test_different_vendor_is_not_duplicate():
    """
    Same date and amount are not enough.

    Vendor must also match.
    """

    df = pd.DataFrame(
        [
            {
                "transaction_id": "T0001",
                "date": "2026-08-19",
                "vendor": "AWS",
                "amount": 2500.00,
                "currency": "SGD",
            },
            {
                "transaction_id": "T0002",
                "date": "2026-08-19",
                "vendor": "Google",
                "amount": 2500.00,
                "currency": "SGD",
            },
        ]
    )

    signals = detect_duplicate_candidates(df)

    assert signals == []


def test_different_date_is_not_duplicate():
    """
    Same vendor and amount are not enough.

    Date must also match.
    """

    df = pd.DataFrame(
        [
            {
                "transaction_id": "T0001",
                "date": "2026-08-19",
                "vendor": "AWS",
                "amount": 2500.00,
                "currency": "SGD",
            },
            {
                "transaction_id": "T0002",
                "date": "2026-08-20",
                "vendor": "AWS",
                "amount": 2500.00,
                "currency": "SGD",
            },
        ]
    )

    signals = detect_duplicate_candidates(df)

    assert signals == []


# =========================================================
# COMPLETE CONTROL ENGINE TEST
# =========================================================

def test_run_financial_controls_combines_controls():
    """
    The control orchestrator should combine signals
    from all deterministic controls.
    """

    df = pd.DataFrame(
        [
            {
                "transaction_id": "T0001",
                "date": "2026-08-19",
                "vendor": "AWS",
                "amount": 15000.00,
                "currency": "SGD",
            },
            {
                "transaction_id": "T0002",
                "date": "2026-08-19",
                "vendor": "AWS",
                "amount": 15000.00,
                "currency": "SGD",
            },
            {
                "transaction_id": "T0003",
                "date": "2026-08-20",
                "vendor": "Google",
                "amount": 500.00,
                "currency": "SGD",
            },
        ]
    )

    signals = run_financial_controls(
        df,
        high_value_thresholds={
            "SGD": 10000.00,
        },
    )

    high_value_signals = [
        signal
        for signal in signals
        if signal["signal_type"] == "HIGH_VALUE"
    ]

    duplicate_signals = [
        signal
        for signal in signals
        if signal["signal_type"]
        == "DUPLICATE_CANDIDATE"
    ]

    assert len(high_value_signals) == 2
    assert len(duplicate_signals) == 2
    assert len(signals) == 4
    