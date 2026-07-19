"""Sweep space definitions and config generation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from quadbalance.asset_universe import SWEEP_STOCK_SUB_SPLITS
from quadbalance.portfolio_templates import ALLOCATION_VARIANTS

if TYPE_CHECKING:
    from quadbalance.config import StrategyConfig

BondVariant = Literal["B1", "B2", "B3"]
DcaMethod = Literal["proportional", "underweight"]

SWEEP_BOND_VARIANTS: tuple[BondVariant, ...] = ("B1", "B2", "B3")
SWEEP_DCA_METHODS: tuple[DcaMethod, ...] = ("proportional", "underweight")
SWEEP_REBALANCE_THRESHOLDS: tuple[float, ...] = (0.05,)
SWEEP_ALLOCATIONS: tuple[str, ...] = tuple(ALLOCATION_VARIANTS.keys())


def generate_sweep_configs() -> list["StrategyConfig"]:
    from quadbalance.config import StrategyConfig

    configs: list[StrategyConfig] = []
    for alloc_name in SWEEP_ALLOCATIONS:
        s, b, g, c = ALLOCATION_VARIANTS[alloc_name]
        for bond in SWEEP_BOND_VARIANTS:
            for dca in SWEEP_DCA_METHODS:
                for threshold in SWEEP_REBALANCE_THRESHOLDS:
                    for stock_sub_split in SWEEP_STOCK_SUB_SPLITS:
                        configs.append(
                            StrategyConfig(
                                allocation_name=alloc_name,
                                stocks=s,
                                bonds=b,
                                gold=g,
                                cash=c,
                                bond_variant=bond,
                                dca_method=dca,
                                rebalance_threshold=threshold,
                                stock_sub_split=stock_sub_split,
                            )
                        )
    return configs
