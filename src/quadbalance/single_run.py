"""Validate a single StrategyConfig and write run artifacts (no full sweep)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from quadbalance.artifacts import write_run_artifacts
from quadbalance.asset_universe import QDII_BACKUP_SYMBOLS
from quadbalance.config import StrategyConfig
from quadbalance.data import load_market_data
from quadbalance.evaluation_pipeline import EvaluationPipelineResult, run_evaluation_pipeline
from quadbalance.profile_thresholds import DEFAULT_INVESTOR_PROFILES
from quadbalance.sweep import collect_required_symbols
from quadbalance.validation import ValidationResult


def run_single_config(
    config: StrategyConfig,
    output_dir: Path,
    *,
    use_cache: bool = True,
    intended_profile: str | None = None,
    profile_thresholds_path: Path | None = None,
    include_long_term: bool = True,
    prices: pd.DataFrame | None = None,
    backup_prices: dict[str, pd.Series] | None = None,
    allow_soft_lock: bool = False,
) -> tuple[ValidationResult, StrategyConfig, Any]:
    """
    Deep-validate one configuration and write artifacts + strategy-lock.md under output_dir.
    Does not enumerate the sweep space.
    Active lock document is written only when lockable (or allow_soft_lock=True for inspection).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    if prices is None:
        required_symbols = collect_required_symbols([config])
        required_backup = sorted(
            set(QDII_BACKUP_SYMBOLS)
            | {sym for sym in config.simulation_symbols() if config.is_qdii_symbol(sym)}
        )
        prices, backup_prices, _ = load_market_data(
            symbols=required_symbols,
            backup_symbols=tuple(required_backup),
            use_cache=use_cache,
        )
    assert backup_prices is not None

    pipeline = run_evaluation_pipeline(
        config,
        prices,
        backup_prices=backup_prices,
        profile_thresholds_path=profile_thresholds_path,
        include_long_term=include_long_term,
    )
    sim_result = pipeline.sim_result
    metrics = pipeline.metrics
    validation = pipeline.validation

    from quadbalance.reporting import generate_lock_document

    if validation.lockable or allow_soft_lock:
        status = "locked" if validation.lockable else "validated-not-lockable"
        generate_lock_document(
            config,
            sim_result,
            validation,
            output_dir / "strategy-lock.md",
            intended_profile=intended_profile,
            lock_status=status,
            inflation_annual=0.03,
        )
    else:
        (output_dir / "strategy-lock.md").write_text(
            "# Strategy Lock Document\n\n"
            f"**Status:** not-lockable\n\n"
            f"Configuration `{config.config_id}` passed={validation.passed} but is not lockable "
            f"without human sign-off. Material reviews:\n\n"
            + "\n".join(f"- {item}" for item in validation.material_needs_review)
            + "\n",
            encoding="utf-8",
        )
    write_run_artifacts(
        output_dir,
        config,
        sim_result,
        validation,
        DEFAULT_INVESTOR_PROFILES,
        validation.lifecycle_results,
    )
    # Also emit a one-row sweep_results-like file for UI consistency
    pd.DataFrame(
        [
            {
                "config_id": config.config_id,
                "validation_passed": validation.passed,
                "lockable": validation.lockable,
                "failure_reasons": "; ".join(validation.failure_reasons),
                "needs_review": "; ".join(validation.needs_review),
                "material_needs_review": "; ".join(validation.material_needs_review),
                "annualized_return": metrics.annualized_return,
                "max_drawdown": metrics.max_drawdown,
                "effective_start": sim_result.effective_start,
            }
        ]
    ).to_csv(output_dir / "sweep_results.csv", index=False)

    return validation, config, sim_result
