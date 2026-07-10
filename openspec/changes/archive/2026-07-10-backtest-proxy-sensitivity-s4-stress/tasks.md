## 1. Data Layer — Proxy Perturbation

- [x] 1.1 Add `perturb_price_segment(series, end_date, annual_drift)` to data layer with handoff boundary preservation
- [x] 1.2 Add `build_perturbed_price_matrix(proxy_key, drift, use_cache)` that applies drift to one proxy mapping only
- [x] 1.3 Add unit tests for perturbation boundary continuity and segment isolation

## 2. Proxy Sensitivity Module

- [x] 2.1 Create `src/quadbalance/proxy_sensitivity.py` with scenario generator (baseline + 4 drifts × 5 proxies)
- [x] 2.2 Implement `compute_segment_metrics(daily_values)` for proxy_era (2013–2016) and primary_era (2017+)
- [x] 2.3 Implement `run_sensitivity(config, prices, meta)` returning scenario metrics and impact summary
- [x] 2.4 Write `output/proxy_sensitivity.csv` and `output/segment_metrics.csv`

## 3. S4 Five-Year Path Stress Test

- [x] 3.1 Add `cap_bond_annual_returns(prices, config, window_years, cap_rate)` price path modifier in stress.py
- [x] 3.2 Replace S4 static shock with full `simulate()` re-run on modified price path
- [x] 3.3 Report S4: shock window years, 5-year cumulative return, worst year in window, window annualized return
- [x] 3.4 Add unit test for bond cap ensuring each year in window ≤ 2% annual return

## 4. Integration

- [x] 4.1 Wire sensitivity analysis into `sweep.py` after first-pass lock (locked config only by default)
- [x] 4.2 Add `--full-sensitivity` CLI flag to run sensitivity for all 48 configurations
- [x] 4.3 Extend `validation.py` lock document with Proxy Sensitivity Summary and S4 Five-Year Path sections
- [x] 4.4 Run full `uv run quadbalance` and verify new output files and lock document sections

## 5. Validation

- [x] 5.1 Run `openspec validate --change backtest-proxy-sensitivity-s4-stress` and fix any errors
- [x] 5.2 Confirm S4 path results differ from old single-year static S4 for locked configuration
