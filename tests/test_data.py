"""Tests for price data stitching."""

from __future__ import annotations

import pandas as pd

from quadbalance.data import perturb_price_segment, stitch_with_proxy


def test_stitch_with_proxy_scales_at_handoff():
    primary = pd.Series(
        [2.0, 2.1, 2.2],
        index=pd.to_datetime(["2020-01-02", "2020-01-03", "2020-01-06"]),
        name="primary",
    )
    proxy = pd.Series(
        [1.0, 1.1, 1.2, 1.3],
        index=pd.to_datetime(["2019-12-30", "2019-12-31", "2020-01-02", "2020-01-03"]),
        name="proxy",
    )

    stitched, usage = stitch_with_proxy(primary, proxy)

    assert usage is not None
    assert usage.handoff == "2020-01-02"
    assert stitched.loc["2020-01-02"] == 2.0
    # last proxy before handoff is 2019-12-31 @ 1.1, scale = 2.0/1.1
    assert abs(stitched.loc["2019-12-31"] - (1.1 * (2.0 / 1.1))) < 1e-9
    assert len(stitched) == 5


def test_stitch_without_proxy_history_returns_primary():
    primary = pd.Series(
        [2.0, 2.1],
        index=pd.to_datetime(["2020-01-02", "2020-01-03"]),
        name="primary",
    )
    proxy = pd.Series(
        [1.0, 1.1],
        index=pd.to_datetime(["2020-01-02", "2020-01-03"]),
        name="proxy",
    )

    stitched, usage = stitch_with_proxy(primary, proxy)

    assert usage is None
    pd.testing.assert_series_equal(stitched, primary)


def test_perturb_preserves_handoff_boundary():
    idx = pd.bdate_range("2019-12-01", "2020-01-03")
    series = pd.Series([1.0 * (1.0002 ** i) for i in range(len(idx))], index=idx, name="test")
    handoff = pd.Timestamp("2020-01-02")

    perturbed = perturb_price_segment(series, handoff, 0.02)
    pre_handoff = series.index < handoff

    assert not perturbed.loc[pre_handoff].equals(series.loc[pre_handoff])
    assert perturbed.loc[handoff] == series.loc[handoff]
    assert (perturbed.loc[series.index >= handoff] == series.loc[series.index >= handoff]).all()


def test_perturb_does_not_affect_post_handoff():
    idx = pd.bdate_range("2020-01-02", periods=10)
    series = pd.Series([1.0 * (1.001**i) for i in range(10)], index=idx)
    handoff = pd.Timestamp("2020-01-05")

    perturbed = perturb_price_segment(series, handoff, -0.02)
    post = series.index >= handoff

    pd.testing.assert_series_equal(perturbed.loc[post], series.loc[post])


def test_price_matrix_excludes_qdii_backups():
    from quadbalance.config import PRICE_MATRIX_SYMBOLS, QDII_BACKUP_SYMBOLS
    from quadbalance.data import load_price_matrix_with_meta

    for sym in QDII_BACKUP_SYMBOLS:
        assert sym not in PRICE_MATRIX_SYMBOLS

    prices, _ = load_price_matrix_with_meta(use_cache=True)
    for sym in QDII_BACKUP_SYMBOLS:
        assert sym not in prices.columns


def test_price_matrix_start_restored():
    from quadbalance.data import load_price_matrix_with_meta

    prices, _ = load_price_matrix_with_meta(use_cache=True)
    assert prices.index[0] <= pd.Timestamp("2013-08-01")

