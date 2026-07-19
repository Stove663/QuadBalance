"""CLI entry point for QuadBalance."""

from __future__ import annotations

import argparse
from pathlib import Path

from quadbalance.sweep import run_sweep


def main() -> None:
    parser = argparse.ArgumentParser(description="QuadBalance — China four-quadrant portfolio backtest")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output"),
        help="Output directory for reports",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Force re-fetch ETF data from akshare",
    )
    parser.add_argument(
        "--full-sensitivity",
        action="store_true",
        help="Run proxy sensitivity for all passing configurations (default: locked only)",
    )
    parser.add_argument(
        "--intended-profile",
        choices=["accumulation", "balanced_core", "pre_retirement_preservation", "retirement_withdrawal"],
        default=None,
        help="Preferred investor profile used to prioritize the locked configuration",
    )
    parser.add_argument(
        "--profile-thresholds",
        type=Path,
        default=None,
        help="JSON file with per-profile threshold overrides merged onto built-in defaults",
    )
    parser.add_argument(
        "--sign-off-reviewer",
        type=str,
        default=None,
        help="If no naturally lockable config, lock best soft-pass candidate with this reviewer sign-off",
    )
    parser.add_argument(
        "--sign-off-rationale",
        type=str,
        default=None,
        help="Rationale required with --sign-off-reviewer acknowledging material needs_review items",
    )
    args = parser.parse_args()

    if bool(args.sign_off_reviewer) != bool(args.sign_off_rationale):
        parser.error("--sign-off-reviewer and --sign-off-rationale must be supplied together")

    print("Loading data and running parameter sweep...")
    df, validation, config = run_sweep(
        output_dir=args.output,
        use_cache=not args.no_cache,
        full_sensitivity=args.full_sensitivity,
        intended_profile=args.intended_profile,
        profile_thresholds_path=args.profile_thresholds,
        sign_off_reviewer=args.sign_off_reviewer,
        sign_off_rationale=args.sign_off_rationale,
    )

    passed = df["validation_passed"].sum()
    total = len(df)
    print(f"\nSweep complete: {passed}/{total} configurations passed validation")
    print(f"Results written to {args.output / 'sweep_results.csv'}")

    if validation and config:
        print(f"Strategy lock document: {args.output / 'strategy-lock.md'}")
        print(f"Locked configuration: {config.config_id}")
        print(f"Run artifacts: {args.output / 'artifacts'}")
        print(f"Proxy sensitivity: {args.output / 'proxy_sensitivity.csv'}")
        print(f"Segment metrics: {args.output / 'segment_metrics.csv'}")
    else:
        print("No configuration passed all acceptance criteria.")
        best = df.loc[df["annualized_return"].idxmax()]
        print(
            f"Best by return: {best['config_id']} "
            f"({best['annualized_return']:.2%} ann., {best['max_drawdown']:.2%} MDD)"
        )


if __name__ == "__main__":
    main()
