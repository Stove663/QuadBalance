"""Product-level risk scoring for fund implementation risk."""

from __future__ import annotations

from dataclasses import dataclass, field

from quadbalance.asset_universe import CASH_SYMBOL, GOLD_SYMBOL, QDII_SYMBOL
from quadbalance.config import StrategyConfig
from quadbalance.instrument_catalog import BACKTEST_PROXIES, INSTRUMENT_NAMES


@dataclass
class ProductRiskResult:
    symbol: str
    name: str
    quadrant: str
    weight: float
    score: int
    classification: str
    reasons: list[str] = field(default_factory=list)


@dataclass
class ProductRiskSummary:
    weighted_score: float
    worst_classification: str
    results: list[ProductRiskResult]
    reasons: list[str] = field(default_factory=list)


def _classify_score(score: int) -> str:
    if score >= 70:
        return "thesis-broken"
    if score >= 40:
        return "review-required"
    return "normal"


def _score_symbol(config: StrategyConfig, symbol: str, weight: float) -> ProductRiskResult:
    quadrant = config.quadrant_for_symbol(symbol)
    score = 10
    reasons: list[str] = []
    if symbol == QDII_SYMBOL or config.is_qdii_symbol(symbol):
        score += 35
        reasons.append("QDII product has quota, FX, premium/discount, and cross-market settlement risk")
    if symbol in BACKTEST_PROXIES:
        score += 10
        reasons.append("backtest relies on proxy history before primary fund inception")
    if symbol == GOLD_SYMBOL:
        score += 15
        reasons.append("gold fund can face hedge failure and ETF-link tracking friction")
    if symbol == CASH_SYMBOL:
        score += 15
        reasons.append("cash-like fund can face quick-redemption limits and negative real yield")
    if quadrant == "bonds":
        score += 20
        reasons.append("bond fund can face duration shock, redemption pressure, and valuation liquidity risk")
    if weight >= 0.25:
        score += 10
        reasons.append("large position weight increases product-level concentration")
    score = min(score, 100)
    return ProductRiskResult(symbol, INSTRUMENT_NAMES.get(symbol, symbol), quadrant, weight, score, _classify_score(score), reasons)


def assess_product_risk(config: StrategyConfig) -> ProductRiskSummary:
    weights = config.instrument_weights()
    results = [_score_symbol(config, symbol, weight) for symbol, weight in sorted(weights.items())]
    weighted_score = sum(r.score * r.weight for r in results)
    order = {"normal": 0, "review-required": 1, "thesis-broken": 2}
    worst = max((r.classification for r in results), key=lambda c: order[c], default="normal")
    reasons: list[str] = []
    if weighted_score >= 40:
        reasons.append("weighted product implementation risk requires review")
    if any(r.classification == "thesis-broken" for r in results):
        reasons.append("at least one product-level sleeve breaches the product risk fail floor")
    return ProductRiskSummary(weighted_score, worst, results, reasons)
