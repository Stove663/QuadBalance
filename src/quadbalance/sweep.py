"""Parameter sweep orchestration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from quadbalance.benchmarks import run_benchmarks
from quadbalance.config import StrategyConfig, generate_sweep_configs
from quadbalance.data import load_backup_prices, load_price_matrix_with_meta
from quadbalance.metrics import cash_risk_free_rate, compute_metrics
from quadbalance.proxy_sensitivity import (
    SensitivitySummary,
    run_sensitivity,
    write_sensitivity_outputs,
)
from quadbalance.simulator import simulate
from quadbalance.stress import S4PathResult, run_stress_tests
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
    qdii_fill_rate: float
    avg_pending_cash: float
    max_pending_cash: float
    pending_cash_days: int
    avg_qdii_weight_gap: float
    rebalance_shortfall_events: int
    total_rebalance_shortfall_cny: float
    max_post_rebalance_deviation: float


def run_sweep(
    output_dir: Path = Path("output"),
    use_cache: bool = True,
    full_sensitivity: bool = False,
) -> tuple[pd.DataFrame, ValidationResult | None, StrategyConfig | None]:
    """Run full parameter sweep and return results."""
    prices, price_meta = load_price_matrix_with_meta(use_cache=use_cache)
    backup_prices = load_backup_prices(use_cache=use_cache)
    benchmarks = run_benchmarks(prices)
    rf = cash_risk_free_rate(prices)

    rows: list[SweepRow] = []
    first_pass: ValidationResult | None = None
    first_pass_config: StrategyConfig | None = None
    first_pass_result = None
    first_s4_path: S4PathResult | None = None
    sensitivity_frames: list[pd.DataFrame] = []

    for config in generate_sweep_configs():
        result = simulate(prices, config, backup_prices=backup_prices)
        no_rebal = simulate(prices, config, enable_rebalance=False, backup_prices=backup_prices)
        metrics = compute_metrics(result, config, prices, rf, no_rebal)
        stress, s4_path = run_stress_tests(config, result, prices, backup_prices)
        validation = evaluate_acceptance(config, metrics, benchmarks, stress)
        qm = result.qdii_metrics
        rm = result.rebalance_metrics

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
                qdii_fill_rate=qm.qdii_fill_rate if qm else 1.0,
                avg_pending_cash=qm.avg_pending_cash if qm else 0.0,
                max_pending_cash=qm.max_pending_cash if qm else 0.0,
                pending_cash_days=qm.pending_cash_days if qm else 0,
                avg_qdii_weight_gap=qm.avg_qdii_weight_gap if qm else 0.0,
                rebalance_shortfall_events=rm.shortfall_event_count if rm else 0,
                total_rebalance_shortfall_cny=rm.total_shortfall_cny if rm else 0.0,
                max_post_rebalance_deviation=rm.max_post_rebalance_deviation if rm else 0.0,
            )
        )

        if validation.passed and first_pass is None:
            first_pass = validation
            first_pass_config = config
            first_pass_result = result
            first_s4_path = s4_path

        if full_sensitivity and validation.passed:
            _, _, sens_df = run_sensitivity(
                config, prices, price_meta, benchmarks, rf, backup_prices=backup_prices
            )
            sens_df = sens_df.copy()
            sens_df.insert(0, "config_id", config.config_id)
            sensitivity_frames.append(sens_df)

    df = pd.DataFrame([asdict(r) for r in rows])
    output_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_dir / "sweep_results.csv", index=False)

    if first_pass_config is not None and first_pass_result is not None and first_pass is not None:
        sensitivity_summary, segments, sens_df = run_sensitivity(
            first_pass_config,
            prices,
            price_meta,
            benchmarks,
            rf,
            backup_prices=backup_prices,
        )
        if full_sensitivity and sensitivity_frames:
            pd.concat(sensitivity_frames, ignore_index=True).to_csv(
                output_dir / "proxy_sensitivity.csv", index=False
            )
        else:
            write_sensitivity_outputs(
                sensitivity_summary, segments, sens_df, output_dir, first_pass_config.config_id
            )

        generate_lock_document(
            first_pass_config,
            first_pass_result,
            first_pass,
            output_dir / "strategy-lock.md",
            price_meta=price_meta,
            sensitivity_summary=sensitivity_summary,
            s4_path=first_s4_path,
        )

    return df, first_pass, first_pass_config
