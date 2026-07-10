"""Parameter sweep orchestration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from quadbalance.benchmarks import run_benchmarks
from quadbalance.config import StrategyConfig, generate_sweep_configs
from quadbalance.data import load_price_matrix
from quadbalance.metrics import cash_risk_free_rate, compute_metrics
from quadbalance.simulator import simulate
from quadbalance.stress import run_stress_tests
from quadbalance.validation import (
    ValidationResult,
    evaluate_acceptance,
    generate_lock_document,
)


@dataclass
class SweepRow:
    config_id: str
    allocation: str
    bond_variant: str
    dca_method: str
    rebalance_threshold: float
    annualized_return: float
    annualized_volatility: float
    max_drawdown: float
    sharpe_ratio: float
    positive_years_pct: float
    rebalance_premium: float
    worst_year_return: float
    validation_passed: bool
    failure_reasons: str


def run_sweep(
    output_dir: Path = Path("output"),
    use_cache: bool = True,
) -> tuple[pd.DataFrame, ValidationResult | None, StrategyConfig | None]:
    """Run full parameter sweep and return results."""
    prices = load_price_matrix(use_cache=use_cache)
    benchmarks = run_benchmarks(prices)
    rf = cash_risk_free_rate(prices)

    rows: list[SweepRow] = []
    first_pass: ValidationResult | None = None
    first_pass_config: StrategyConfig | None = None

    for config in generate_sweep_configs():
        result = simulate(prices, config)
        no_rebal = simulate(prices, config, enable_rebalance=False)
        metrics = compute_metrics(result, config, prices, rf, no_rebal)
        stress = run_stress_tests(config, result, prices)
        validation = evaluate_acceptance(config, metrics, benchmarks, stress)

        rows.append(
            SweepRow(
                config_id=config.config_id,
                allocation=config.allocation_name,
                bond_variant=config.bond_variant,
                dca_method=config.dca_method,
                rebalance_threshold=config.rebalance_threshold,
                annualized_return=metrics.annualized_return,
                annualized_volatility=metrics.annualized_volatility,
                max_drawdown=metrics.max_drawdown,
                sharpe_ratio=metrics.sharpe_ratio,
                positive_years_pct=metrics.positive_years_pct,
                rebalance_premium=metrics.rebalance_premium,
                worst_year_return=metrics.worst_year_return,
                validation_passed=validation.passed,
                failure_reasons="; ".join(validation.failure_reasons),
            )
        )

        if validation.passed and first_pass is None:
            first_pass = validation
            first_pass_config = config
            generate_lock_document(
                config, result, validation, output_dir / "strategy-lock.md"
            )

    df = pd.DataFrame([asdict(r) for r in rows])
    output_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_dir / "sweep_results.csv", index=False)
    return df, first_pass, first_pass_config
