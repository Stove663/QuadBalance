"""Parameter sweep orchestration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from quadbalance.benchmarks import run_benchmarks
from quadbalance.config import StrategyConfig
from quadbalance.sweep_space import generate_sweep_configs
from quadbalance.data import load_backup_prices, load_price_matrix_with_meta
from quadbalance.metrics import DEFAULT_INVESTOR_PROFILES, cash_risk_free_rate, classify_suitability, compute_metrics
from quadbalance.proxy_sensitivity import run_sensitivity, write_sensitivity_outputs
from quadbalance.reporting import generate_lock_document
from quadbalance.simulator import LifecycleResult, simulate, simulate_lifecycle
from quadbalance.stress import S4PathResult, run_stress_tests
from quadbalance.sweep_constants import (
    DEFAULT_INFLATION_ANN,
    SENSITIVITY_OUTPUT_FILENAME,
    STRATEGY_LOCK_FILENAME,
    SWEEP_RESULTS_FILENAME,
)
from quadbalance.validation import ValidationResult, evaluate_acceptance


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
    real_annualized_return: float
    real_terminal_wealth: float
    worst_rolling_3y_real_return: float
    longest_underwater_days: int
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
    accumulation_suitability: str
    balanced_core_suitability: str
    pre_retirement_preservation_suitability: str
    retirement_withdrawal_suitability: str


def _profile_rank(classification: str) -> int:
    order = {"suitable": 2, "caution": 1, "unsuitable": 0}
    return order.get(classification, 0)


def _select_first_pass(
    current: tuple[ValidationResult, StrategyConfig, pd.DataFrame],
    candidate: tuple[ValidationResult, StrategyConfig, pd.DataFrame],
    intended_profile: str | None,
) -> tuple[ValidationResult, StrategyConfig, pd.DataFrame]:
    if intended_profile is None:
        return current
    curr_validation, _, _ = current
    cand_validation, _, _ = candidate
    curr_score = _profile_rank(curr_validation.profile_suitability.get(intended_profile, {}).get("classification", "unsuitable"))
    cand_score = _profile_rank(cand_validation.profile_suitability.get(intended_profile, {}).get("classification", "unsuitable"))
    return candidate if cand_score > curr_score else current


def _attach_profile_defaults(validation: ValidationResult) -> None:
    for profile in DEFAULT_INVESTOR_PROFILES:
        validation.profile_suitability.setdefault(profile.profile_id, {"classification": "caution", "reasons": []})


def _build_lifecycle_results(prices: pd.DataFrame, config: StrategyConfig) -> list[LifecycleResult]:
    return [
        simulate_lifecycle(prices, config, "no_dca", interrupt_months=999),
        simulate_lifecycle(prices, config, "dca_interrupt_12m", interrupt_months=12),
        simulate_lifecycle(prices, config, "dca_interrupt_24m", interrupt_months=24),
        simulate_lifecycle(prices, config, "dca_interrupt_36m", interrupt_months=36),
        simulate_lifecycle(prices, config, "one_time_liquidity_20pct"),
        simulate_lifecycle(prices, config, "withdrawal_3pct", withdrawal_rate=0.03, withdrawal_mode="annual"),
        simulate_lifecycle(prices, config, "withdrawal_4pct", withdrawal_rate=0.04, withdrawal_mode="annual"),
        simulate_lifecycle(prices, config, "withdrawal_5pct", withdrawal_rate=0.05, withdrawal_mode="annual"),
        simulate_lifecycle(prices, config, "bear_market_retirement_start", withdrawal_rate=0.04, withdrawal_mode="annual"),
    ]


def _populate_row(
    config: StrategyConfig,
    metrics,
    validation: ValidationResult,
    qm,
    rm,
) -> SweepRow:
    return SweepRow(
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
        real_annualized_return=metrics.real_annualized_return,
        real_terminal_wealth=metrics.real_terminal_wealth,
        worst_rolling_3y_real_return=metrics.worst_rolling_3y_real_return,
        longest_underwater_days=metrics.longest_underwater_days,
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
        accumulation_suitability=validation.profile_suitability["accumulation"]["classification"],
        balanced_core_suitability=validation.profile_suitability["balanced_core"]["classification"],
        pre_retirement_preservation_suitability=validation.profile_suitability["pre_retirement_preservation"]["classification"],
        retirement_withdrawal_suitability=validation.profile_suitability["retirement_withdrawal"]["classification"],
    )


def run_sweep(
    output_dir: Path = Path("output"),
    use_cache: bool = True,
    full_sensitivity: bool = False,
    intended_profile: str | None = None,
) -> tuple[pd.DataFrame, ValidationResult | None, StrategyConfig | None]:
    """Run full parameter sweep and return results."""
    prices, price_meta = load_price_matrix_with_meta(use_cache=use_cache)
    backup_prices = load_backup_prices(use_cache=use_cache)
    benchmarks = run_benchmarks(prices)
    rf = cash_risk_free_rate(prices)

    rows: list[SweepRow] = []
    first_pass_bundle: tuple[ValidationResult, StrategyConfig, pd.DataFrame] | None = None
    first_s4_path: S4PathResult | None = None
    sensitivity_frames: list[pd.DataFrame] = []

    for config in generate_sweep_configs():
        result = simulate(prices, config, backup_prices=backup_prices)
        no_rebal = simulate(prices, config, enable_rebalance=False, backup_prices=backup_prices)
        metrics = compute_metrics(result, config, prices, rf, no_rebal, inflation_annual=DEFAULT_INFLATION_ANN)
        stress, s4_path = run_stress_tests(config, result, prices, backup_prices)
        validation = evaluate_acceptance(config, metrics, benchmarks, stress)
        qm = result.qdii_metrics
        rm = result.rebalance_metrics
        qdii_fill = qm.qdii_fill_rate if qm else 1.0
        qdii_gap = qm.avg_qdii_weight_gap if qm else 0.0
        qdii_friction_months = qm.qdii_friction_months if qm else 0
        qdii_recovery_months = qm.qdii_recovery_months if qm else 0
        suitability = classify_suitability(config, metrics, qdii_fill, qdii_gap, qdii_friction_months, qdii_recovery_months)
        validation.profile_suitability = {k: {"classification": v.classification, "reasons": v.reasons} for k, v in suitability.items()}
        _attach_profile_defaults(validation)

        rows.append(_populate_row(config, metrics, validation, qm, rm))

        if validation.passed:
            candidate_bundle = (validation, config, result)
            if first_pass_bundle is None:
                first_pass_bundle = candidate_bundle
                first_s4_path = s4_path
            else:
                first_pass_bundle = _select_first_pass(first_pass_bundle, candidate_bundle, intended_profile)

        if full_sensitivity and validation.passed:
            _, _, sens_df = run_sensitivity(
                config, prices, price_meta, benchmarks, rf, backup_prices=backup_prices
            )
            sens_df = sens_df.copy()
            sens_df.insert(0, "config_id", config.config_id)
            sensitivity_frames.append(sens_df)

    df = pd.DataFrame([asdict(r) for r in rows])
    output_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_dir / SWEEP_RESULTS_FILENAME, index=False)

    if first_pass_bundle is not None:
        first_pass, first_pass_config, first_pass_result = first_pass_bundle
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
                output_dir / SENSITIVITY_OUTPUT_FILENAME, index=False
            )
        else:
            write_sensitivity_outputs(
                sensitivity_summary, segments, sens_df, output_dir, first_pass_config.config_id
            )

        first_pass.lifecycle_results = _build_lifecycle_results(prices, first_pass_config)
        generate_lock_document(
            first_pass_config,
            first_pass_result,
            first_pass,
            output_dir / STRATEGY_LOCK_FILENAME,
            price_meta=price_meta,
            sensitivity_summary=sensitivity_summary,
            s4_path=first_s4_path,
        )

    return df, first_pass_bundle[0] if first_pass_bundle else None, first_pass_bundle[1] if first_pass_bundle else None
