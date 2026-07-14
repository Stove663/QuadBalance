"""Strategy configuration definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from quadbalance.asset_universe import (
    ALL_SYMBOLS,
    BENCHMARK_BOND,
    BENCHMARK_CASH,
    BENCHMARK_CSI300,
    BOND_VARIANTS,
    CASH_SYMBOL,
    DEFAULT_STOCK_SUB_SPLIT,
    ENABLE_QDII_QUOTA,
    GOLD_SYMBOL,
    PRICE_MATRIX_SYMBOLS,
    QDII_BACKUP_SYMBOLS,
    QDII_SYMBOL,
    STOCK_SUB_WEIGHTS,
    StockSubSplit,
    Quadrant,
    stock_sub_weights,
)
from quadbalance.instrument_pool import default_qdii_daily_caps

DcaMethod = Literal["proportional", "underweight"]
BondVariant = Literal["B1", "B2", "B3"]


@dataclass(frozen=True)
class StrategyConfig:
    allocation_name: str
    stocks: float
    bonds: float
    gold: float
    cash: float
    bond_variant: BondVariant
    dca_method: DcaMethod
    rebalance_threshold: float
    stock_sub_split: StockSubSplit = DEFAULT_STOCK_SUB_SPLIT
    qdii_premium: float = 0.0
    enable_qdii_quota: bool = ENABLE_QDII_QUOTA
    qdii_daily_caps: dict[str, float] | None = None

    def __post_init__(self) -> None:
        if self.qdii_daily_caps is None:
            object.__setattr__(self, "qdii_daily_caps", default_qdii_daily_caps())

    @property
    def config_id(self) -> str:
        dca = "prop" if self.dca_method == "proportional" else "uw"
        pct = int(self.rebalance_threshold * 100)
        return f"{self.allocation_name}_{self.bond_variant}_{dca}_{pct}pct_s{self.stock_sub_split}"

    @property
    def stock_weights(self) -> dict[str, float]:
        return stock_sub_weights(self.stock_sub_split)

    @property
    def quadrant_weights(self) -> dict[Quadrant, float]:
        return {
            "stocks": self.stocks,
            "bonds": self.bonds,
            "gold": self.gold,
            "cash": self.cash,
        }

    def instrument_weights(self) -> dict[str, float]:
        weights: dict[str, float] = {}
        for sym, sub in self.stock_weights.items():
            weights[sym] = self.stocks * sub
        for sym, sub in BOND_VARIANTS[self.bond_variant].items():
            weights[sym] = weights.get(sym, 0.0) + self.bonds * sub
        weights[GOLD_SYMBOL] = self.gold
        weights[CASH_SYMBOL] = self.cash
        return weights

    def symbols(self) -> list[str]:
        syms = list(self.stock_weights.keys())
        syms.extend(BOND_VARIANTS[self.bond_variant].keys())
        syms.extend([GOLD_SYMBOL, CASH_SYMBOL])
        return sorted(set(syms))

    def simulation_symbols(self) -> list[str]:
        syms = set(self.symbols())
        if self.enable_qdii_quota:
            from quadbalance.instrument_pool import qdii_pool_codes

            syms.update(qdii_pool_codes())
        return sorted(syms)

    def is_qdii_symbol(self, symbol: str) -> bool:
        from quadbalance.instrument_pool import qdii_pool_codes

        return symbol in qdii_pool_codes()

    def qdii_target_weight(self) -> float:
        return self.stocks * self.stock_weights[QDII_SYMBOL]

    def quadrant_for_symbol(self, symbol: str) -> Quadrant:
        if symbol in self.stock_weights or self.is_qdii_symbol(symbol):
            return "stocks"
        if symbol in BOND_VARIANTS[self.bond_variant]:
            return "bonds"
        if symbol == GOLD_SYMBOL:
            return "gold"
        return "cash"

    def sub_weight(self, symbol: str) -> float:
        if symbol in self.stock_weights:
            return self.stock_weights[symbol]
        if symbol in BOND_VARIANTS[self.bond_variant]:
            return BOND_VARIANTS[self.bond_variant][symbol]
        return 1.0


def generate_sweep_configs() -> list[StrategyConfig]:
    from quadbalance.sweep_space import generate_sweep_configs as _generate_sweep_configs

    return _generate_sweep_configs()


# Backward-compatible exports for older imports.
PRICE_MATRIX_SYMBOLS = PRICE_MATRIX_SYMBOLS
QDII_BACKUP_SYMBOLS = QDII_BACKUP_SYMBOLS
STOCK_SUB_WEIGHTS = STOCK_SUB_WEIGHTS
