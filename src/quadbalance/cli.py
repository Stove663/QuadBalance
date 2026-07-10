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
    args = parser.parse_args()

    print("Loading data and running parameter sweep...")
    df, validation, config = run_sweep(
        output_dir=args.output,
        use_cache=not args.no_cache,
        full_sensitivity=args.full_sensitivity,
    )

    passed = df["validation_passed"].sum()
    total = len(df)
    print(f"\nSweep complete: {passed}/{total} configurations passed validation")
    print(f"Results written to {args.output / 'sweep_results.csv'}")

    if validation and config:
        print(f"Strategy lock document: {args.output / 'strategy-lock.md'}")
        print(f"Locked configuration: {config.config_id}")
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
