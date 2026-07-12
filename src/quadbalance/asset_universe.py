"""Asset universe constants."""

from __future__ import annotations

from typing import Literal

Quadrant = Literal["stocks", "bonds", "gold", "cash"]
AssetChannel = Literal["otc", "exchange"]

# Off-exchange (场外) open-end funds — locked strategy asset universe
ASSET_CHANNEL: AssetChannel = "otc"

PRIMARY_START = "2013-01-01"
BASE_CAPITAL = 1_000_000.0
MONTHLY_CONTRIBUTION = 10_000.0
# Deprecated: use quadbalance.fees.purchase_fee_rate / redemption_fee_rate per symbol.
TRANSACTION_COST = 0.001

# Stocks: domestic CSI 300 feeder + S&P 500 QDII (direct index)
STOCK_SUB_WEIGHTS = {"110020": 0.6, "161125": 0.4}
QDII_SYMBOL = "161125"
ENABLE_QDII_QUOTA = True
DEFAULT_QDII_DAILY_CAP = 100.0

GOLD_SYMBOL = "000216"
CASH_SYMBOL = "006874"

BOND_VARIANTS: dict[str, dict[str, float]] = {
    "B1": {"003358": 1.0},  # 嘉实3-5年国债ETF联接A
    "B2": {"003327": 1.0},  # 易方达中债7-10年国开行债券指数A
    "B3": {"003358": 0.5, "003327": 0.5},
}

QDII_BACKUP_SYMBOLS = ("050025", "006075")

# Alignment set: primaries + bond sweep columns only (no QDII backups).
PRICE_MATRIX_SYMBOLS = sorted(
    set(STOCK_SUB_WEIGHTS) | {GOLD_SYMBOL, CASH_SYMBOL} | set(BOND_VARIANTS["B3"])
)

ALL_SYMBOLS = PRICE_MATRIX_SYMBOLS

# Benchmark instruments (场外 feeders aligned with strategy)
BENCHMARK_CSI300 = "110020"
BENCHMARK_BOND = "003358"
BENCHMARK_CASH = CASH_SYMBOL
