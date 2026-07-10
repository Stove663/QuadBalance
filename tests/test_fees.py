"""Tests for per-symbol transaction fees."""

from __future__ import annotations

import pytest

from quadbalance.fees import (
    SIMULATION_SYMBOLS,
    format_fee_assumptions_markdown,
    purchase_fee_rate,
    redemption_fee_rate,
)
from quadbalance.instrument_pool import ALL_INSTRUMENTS
from quadbalance.simulator import _buy


def test_simulation_symbols_have_fees():
    for symbol in SIMULATION_SYMBOLS:
        assert symbol in ALL_INSTRUMENTS
        assert purchase_fee_rate(symbol) >= 0.0
        assert redemption_fee_rate(symbol) == 0.0


def test_purchase_fee_rates():
    assert purchase_fee_rate("110020") == pytest.approx(0.0012)
    assert purchase_fee_rate("161125") == pytest.approx(0.0012)
    assert purchase_fee_rate("050025") == pytest.approx(0.0010)
    assert purchase_fee_rate("006075") == pytest.approx(0.0)
    assert purchase_fee_rate("003358") == pytest.approx(0.0006)
    assert purchase_fee_rate("003327") == pytest.approx(0.0008)
    assert purchase_fee_rate("000216") == pytest.approx(0.0006)
    assert purchase_fee_rate("006874") == pytest.approx(0.0)


def test_unknown_symbol_raises():
    with pytest.raises(KeyError):
        purchase_fee_rate("999999")


def test_buy_applies_per_symbol_fee():
    shares: dict[str, float] = {}
    _buy(shares, "006874", 10_000.0, 1.0)
    assert shares["006874"] == pytest.approx(10_000.0)

    shares = {}
    _buy(shares, "110020", 10_000.0, 1.0)
    assert shares["110020"] == pytest.approx(10_000.0 / 1.0012)


def test_qdii_backup_fee_distinct_from_primary():
    assert purchase_fee_rate("161125") != purchase_fee_rate("050025")
    assert purchase_fee_rate("050025") == pytest.approx(0.0010)


def test_fee_assumptions_markdown_includes_primaries():
    md = format_fee_assumptions_markdown()
    assert "Transaction Fee Assumptions" in md
    assert "110020" in md
    assert "006874" in md
    assert "0%" in md
