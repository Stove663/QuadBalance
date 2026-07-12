"""Instrument names and proxy mappings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from quadbalance.asset_universe import QDII_BACKUP_SYMBOLS

ProxySource = Literal["otc", "etf"]


@dataclass(frozen=True)
class BacktestProxy:
    """Longer-history instrument used before primary fund inception."""

    code: str
    source: ProxySource
    note: str


INSTRUMENT_NAMES: dict[str, str] = {
    "110020": "易方达沪深300ETF联接A",
    "161125": "易方达标普500指数（QDII-LOF）A",
    "050025": "博时标普500ETF联接(QDII)A",
    "006075": "博时标普500ETF联接(QDII)C",
    "003358": "嘉实3-5年国债ETF联接A",
    "003327": "易方达中债7-10年国开行债券指数A",
    "000216": "华安黄金ETF联接A",
    "006874": "泰康现金管家货币A",
    "070009": "嘉实超短债债券A",
    "161119": "易方达中债新综合指数（LOF）A",
    "518880": "华安黄金ETF",
}


def qdii_pool_codes() -> list[str]:
    return ["161125", *QDII_BACKUP_SYMBOLS]


# Primary OTC symbol -> backtest proxy (see instrument_pool backup notes)
BACKTEST_PROXIES: dict[str, BacktestProxy] = {
    "006874": BacktestProxy("070009", "otc", "Cash proxy before 006874 inception"),
    "161125": BacktestProxy("050025", "otc", "QDII proxy before 161125 inception"),
    "003358": BacktestProxy("161119", "otc", "B1 bond proxy before 003358 inception"),
    "003327": BacktestProxy("161119", "otc", "B2 bond proxy before 003327 inception"),
    "000216": BacktestProxy("518880", "etf", "Gold proxy before 000216 inception"),
}
