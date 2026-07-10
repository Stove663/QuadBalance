"""Strategy configuration and parameter sweep definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Quadrant = Literal["stocks", "bonds", "gold", "cash"]
DcaMethod = Literal["proportional", "underweight"]
BondVariant = Literal["B1", "B2", "B3"]
AssetChannel = Literal["otc", "exchange"]

# Off-exchange (场外) open-end funds — locked strategy asset universe
ASSET_CHANNEL: AssetChannel = "otc"

PRIMARY_START = "2013-01-01"
BASE_CAPITAL = 1_000_000.0
MONTHLY_CONTRIBUTION = 10_000.0
TRANSACTION_COST = 0.001  # 0.1% subscription/redemption fee assumption

# Stocks: domestic CSI 300 feeder + S&P 500 QDII (direct index)
STOCK_SUB_WEIGHTS = {"110020": 0.6, "161125": 0.4}
QDII_SYMBOL = "161125"

GOLD_SYMBOL = "000216"
CASH_SYMBOL = "006874"

BOND_VARIANTS: dict[BondVariant, dict[str, float]] = {
    "B1": {"003358": 1.0},  # 嘉实3-5年国债ETF联接A
    "B2": {"003327": 1.0},  # 易方达中债7-10年国开行债券指数A
    "B3": {"003358": 0.5, "003327": 0.5},
}

INSTRUMENT_NAMES: dict[str, str] = {
    "110020": "易方达沪深300ETF联接A",
    "161125": "易方达标普500指数（QDII-LOF）A",
    "050025": "博时标普500ETF联接(QDII)A",
    "003358": "嘉实3-5年国债ETF联接A",
    "003327": "易方达中债7-10年国开行债券指数A",
    "000216": "华安黄金ETF联接A",
    "006874": "泰康现金管家货币A",
}

ALLOCATION_VARIANTS: dict[str, tuple[float, float, float, float]] = {
    "25-25-25-25": (0.25, 0.25, 0.25, 0.25),
    "20-30-25-25": (0.20, 0.30, 0.25, 0.25),
    "30-20-25-25": (0.30, 0.20, 0.25, 0.25),
    "20-25-30-25": (0.20, 0.25, 0.30, 0.25),
}

ALL_SYMBOLS = sorted(
    set(STOCK_SUB_WEIGHTS) | {GOLD_SYMBOL, CASH_SYMBOL} | set(BOND_VARIANTS["B3"])
)

# Benchmark instruments (场外 feeders aligned with strategy)
BENCHMARK_CSI300 = "110020"
BENCHMARK_BOND = "003358"
BENCHMARK_CASH = CASH_SYMBOL


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
    qdii_premium: float = 0.0

    @property
    def config_id(self) -> str:
        dca = "prop" if self.dca_method == "proportional" else "uw"
        pct = int(self.rebalance_threshold * 100)
        return f"{self.allocation_name}_{self.bond_variant}_{dca}_{pct}pct"

    @property
    def quadrant_weights(self) -> dict[Quadrant, float]:
        return {
            "stocks": self.stocks,
            "bonds": self.bonds,
            "gold": self.gold,
            "cash": self.cash,
        }

    def instrument_weights(self) -> dict[str, float]:
        """Portfolio-level target weight per instrument."""
        weights: dict[str, float] = {}
        for sym, sub in STOCK_SUB_WEIGHTS.items():
            weights[sym] = self.stocks * sub
        for sym, sub in BOND_VARIANTS[self.bond_variant].items():
            weights[sym] = weights.get(sym, 0.0) + self.bonds * sub
        weights[GOLD_SYMBOL] = self.gold
        weights[CASH_SYMBOL] = self.cash
        return weights

    def symbols(self) -> list[str]:
        syms = list(STOCK_SUB_WEIGHTS.keys())
        syms.extend(BOND_VARIANTS[self.bond_variant].keys())
        syms.extend([GOLD_SYMBOL, CASH_SYMBOL])
        return sorted(set(syms))

    def quadrant_for_symbol(self, symbol: str) -> Quadrant:
        if symbol in STOCK_SUB_WEIGHTS:
            return "stocks"
        if symbol in BOND_VARIANTS[self.bond_variant]:
            return "bonds"
        if symbol == GOLD_SYMBOL:
            return "gold"
        return "cash"

    def sub_weight(self, symbol: str) -> float:
        if symbol in STOCK_SUB_WEIGHTS:
            return STOCK_SUB_WEIGHTS[symbol]
        if symbol in BOND_VARIANTS[self.bond_variant]:
            return BOND_VARIANTS[self.bond_variant][symbol]
        return 1.0


def generate_sweep_configs() -> list[StrategyConfig]:
    configs: list[StrategyConfig] = []
    for alloc_name, (s, b, g, c) in ALLOCATION_VARIANTS.items():
        for bond in ("B1", "B2", "B3"):
            for dca in ("proportional", "underweight"):
                for threshold in (0.05, 0.10):
                    configs.append(
                        StrategyConfig(
                            allocation_name=alloc_name,
                            stocks=s,
                            bonds=b,
                            gold=g,
                            cash=c,
                            bond_variant=bond,  # type: ignore[arg-type]
                            dca_method=dca,  # type: ignore[arg-type]
                            rebalance_threshold=threshold,
                        )
                    )
    return configs
