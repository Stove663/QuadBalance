## Context

QuadBalance loads ETF/fund prices into a single `DataFrame` and uses `dropna(how="any")` to determine the effective backtest start. After QDII quota simulation, `ALL_SYMBOLS` includes backup funds `050025` and `006075`. The youngest backup (`006075`, listed 2018-06-08) became the alignment bottleneck, pushing `effective_start` from 2013-07-29 to 2018-06-08.

Meanwhile, `161125` already uses `050025` as a stitched proxy before its 2016-12-02 handoff. Holding both `161125` (proxy-stitched) and `050025` (independent backup column) in the same portfolio after handoff is correct, but routing to `050025` before `161125` exists as a primary would duplicate the same underlying exposure.

## Goals / Non-Goals

**Goals:**

- Restore price-matrix alignment to primary (+ proxy-stitched) symbols only; effective start returns to 2013-07-29 or earlier bottleneck (gold proxy)
- Load QDII backup prices separately; join at simulation runtime when the instrument is tradable on that date
- Date-gate QDII pool membership: no `006075` before 2018-06-08; no independent `050025` routing before `161125` handoff
- Disable daily QDII quota during proxy era (dates before `161125` primary inception), when buys go through the stitched column
- Document era boundaries in strategy-lock output

**Non-Goals:**

- Extending gold history before 2013-07-29 (518880 proxy limit)
- Shared-platform QDII quota pooling across backup funds (keep independent caps)
- Changing acceptance criteria thresholds
- Per-fund transaction fees (separate change: `per-fund-transaction-fees`)

## Decisions

### D1: Split alignment symbols from tradable backups

**Decision:** Introduce `PRICE_MATRIX_SYMBOLS` (primaries + bond sweep columns, no QDII backups). Keep `QDII_BACKUP_SYMBOLS` for lazy load only.

**Rationale:** Alignment answers "when can the portfolio start?"; backups answer "what can I buy on day T?". Mixing them caused the 2018 regression.

**Alternatives considered:**
- *Remove only 006075 from ALL_SYMBOLS* (minimal fix) — insufficient; doesn't formalize the pattern or prevent recurrence
- *Outer-join with NaN tolerance* — still requires explicit dropna exclusion logic; less clear than separate sets

### D2: Lazy backup price join in simulator

**Decision:** `load_price_matrix_with_meta()` returns core matrix only. New `load_backup_prices(symbols, use_cache)` returns `dict[str, Series]`. `simulate()` builds `day_prices` by merging core row with available backup prices for that date.

**Rationale:** Backups never participate in `dropna(how="any")`. Simulator already iterates day-by-day — natural join point.

### D3: Date-aware QDII pool function

**Decision:** `qdii_pool_for_date(dt) -> list[str]` in `instrument_pool.py`:

| Era | Dates | Pool |
|-----|-------|------|
| Proxy | < 2016-12-02 | `[161125]` only (column is stitched 050025) |
| Primary + backup1 | 2016-12-02 – 2018-06-07 | `[161125, 050025]` |
| Full pool | ≥ 2018-06-08 | `[161125, 050025, 006075]` |

Inception dates sourced from cached NAV first-available dates, with constants as fallback.

**Rationale:** Matches fund listing reality; avoids buying a fund that didn't exist.

### D4: Proxy-era quota bypass

**Decision:** When `dt < 161125_handoff_date`, skip `enable_qdii_quota` enforcement for QDII buys (treat as unlimited fill through the `161125` column).

**Rationale:** Daily cap on `161125` is meaningless when the fund didn't exist; the column represents historical proxy NAV. Quota friction should apply only post-handoff.

### D5: dropna applies to core matrix only

**Decision:** `load_price_matrix_with_meta()` calls `dropna(how="any")` on `PRICE_MATRIX_SYMBOLS` columns only. `simulate()` calls `dropna(how="any")` on core symbols from `config.symbols()` + bond variants, not backup columns.

**Rationale:** Single choke-point fix with simulator safety net.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Restored 2013 era changes sweep metrics (more quota years) | Document pre/post comparison in tasks; acceptance thresholds unchanged |
| 050025 double exposure if proxy + backup overlap mishandled | Block independent 050025 routing before handoff (D3) |
| `per-fund-transaction-fees` assumes `simulation_symbols()` includes backups | Fee schedule keys backups separately; alignment split documented in design |
| Inception dates drift if akshare data changes | Cache parquet first-date; constants as fallback; test asserts minimum start |

## Migration Plan

1. Implement symbol split + lazy backup load
2. Add `qdii_pool_for_date` and proxy-era quota bypass
3. Update tests for matrix start ≥ 2013-07-29
4. Re-run `uv run quadbalance` and compare `effective_start` + sweep metrics
5. Archive change; sync specs

Rollback: revert to previous `ALL_SYMBOLS` alignment (accepts 2018 start).

## Open Questions

- Should `segment_metrics.csv` proxy_era boundary shift when start moves earlier? (Likely yes — recompute automatically from dates.)
- Coordinate merge order with `per-fund-transaction-fees`: recommend landing this change first.
