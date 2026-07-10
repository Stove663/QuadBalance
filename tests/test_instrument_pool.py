import pandas as pd


def test_instrument_pool_has_primary_and_backup():
    from quadbalance.instrument_pool import POOLS_BY_KEY, backups

    for key, pool in POOLS_BY_KEY.items():
        primaries = [f for f in pool if f.is_primary]
        assert len(primaries) == 1, key
        assert len(backups(key)) >= 1, key


def test_all_primary_codes_in_config():
    from quadbalance.config import (
        CASH_SYMBOL,
        GOLD_SYMBOL,
        QDII_SYMBOL,
        STOCK_SUB_WEIGHTS,
    )
    from quadbalance.instrument_pool import ALL_INSTRUMENTS

    for code in list(STOCK_SUB_WEIGHTS) + [GOLD_SYMBOL, CASH_SYMBOL]:
        assert code in ALL_INSTRUMENTS

    assert QDII_SYMBOL in ALL_INSTRUMENTS


def test_qdii_pool_for_date_eras():
    from quadbalance.instrument_pool import qdii_pool_for_date

    assert qdii_pool_for_date(pd.Timestamp("2015-01-02")) == ["161125"]
    assert qdii_pool_for_date(pd.Timestamp("2017-06-01")) == ["161125", "050025"]
    assert qdii_pool_for_date(pd.Timestamp("2019-01-02")) == [
        "161125",
        "050025",
        "006075",
    ]
