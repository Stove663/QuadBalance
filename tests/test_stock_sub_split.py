"""Tests for Stocks domestic/QDII sub-split variants."""

from __future__ import annotations

from quadbalance.asset_universe import DOMESTIC_STOCK_SYMBOL, QDII_SYMBOL
from quadbalance.config import StrategyConfig


def _base(**kwargs) -> StrategyConfig:
    defaults = dict(
        allocation_name="25-25-25-25",
        stocks=0.25,
        bonds=0.25,
        gold=0.25,
        cash=0.25,
        bond_variant="B1",
        dca_method="proportional",
        rebalance_threshold=0.05,
    )
    defaults.update(kwargs)
    return StrategyConfig(**defaults)


def test_default_stock_sub_split_is_60_40():
    cfg = _base()
    assert cfg.stock_sub_split == "60-40"
    assert cfg.stock_weights[DOMESTIC_STOCK_SYMBOL] == 0.6
    assert cfg.stock_weights[QDII_SYMBOL] == 0.4
    assert abs(cfg.qdii_target_weight() - 0.10) < 1e-12


def test_config_ids_differ_by_stock_sub_split():
    ids = {_base(stock_sub_split=split).config_id for split in ("60-40", "50-50", "40-60")}
    assert len(ids) == 3
    assert all("_s" in cid for cid in ids)


def test_instrument_weights_respect_stock_sub_split():
    cfg = _base(stock_sub_split="40-60")
    weights = cfg.instrument_weights()
    assert abs(weights[DOMESTIC_STOCK_SYMBOL] - 0.25 * 0.4) < 1e-12
    assert abs(weights[QDII_SYMBOL] - 0.25 * 0.6) < 1e-12
    assert abs(cfg.qdii_target_weight() - 0.15) < 1e-12
    assert abs(sum(weights.values()) - 1.0) < 1e-12
