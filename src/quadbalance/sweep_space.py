"""Sweep space definitions and config generation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from quadbalance.portfolio_templates import ALLOCATION_VARIANTS

if TYPE_CHECKING:
    from quadbalance.config import StrategyConfig

BondVariant = Literal["B1", "B2", "B3"]
DcaMethod = Literal["proportional", "underweight"]

SWEEP_BOND_VARIANTS: tuple[BondVariant, ...] = ("B1", "B2", "B3")
SWEEP_DCA_METHODS: tuple[DcaMethod, ...] = ("proportional", "underweight")
SWEEP_REBALANCE_THRESHOLDS: tuple[float, ...] = (0.05, 0.10)


def generate_sweep_configs() -> list["StrategyConfig"]:
    from quadbalance.config import StrategyConfig

    configs: list[StrategyConfig] = []
    for alloc_name, (s, b, g, c) in ALLOCATION_VARIANTS.items():
        for bond in SWEEP_BOND_VARIANTS:
            for dca in SWEEP_DCA_METHODS:
                for threshold in SWEEP_REBALANCE_THRESHOLDS:
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
                        )
                    )
    return configs
