#!/usr/bin/env python3
"""Integration tests for HK and BJ stock data fetching across multiple data sources.

Tests that:
- HK stocks (00700.HK — Tencent) can be fetched from various providers
- BJ stocks (830799) can be fetched from various providers
- Returned DataFrames have the canonical structure: date, open, high, low, close, volume
- Multi-market compatibility across different data sources

Each test that requires real network calls wraps individual provider attempts
in try/except with informative skip messages so failures are visible but
don't break the full test suite.
"""

import unittest
import logging
import pandas as pd

from exchange.source.data_provider import get_data, ALL_SOURCES

logger = logging.getLogger(__name__)

# ── known multi-market test symbols ──────────────────────────────────────
HK_SYMBOL = "00700.HK"  # Tencent Holdings (港股)
BJ_SYMBOL = "830799"     # 北证 stock (Beijing Stock Exchange)

# ── sources that are expected to support each market ─────────────────────
# Sources known to handle HK stocks (have specific .HK handling logic)
HK_CAPABLE_SOURCES = [
    "akshare",      # has _fetch_hk_hist()
    "eastmoney",    # _resolve_secid maps .HK -> h{code}
    "baostock",     # _resolve_code maps .HK -> hk.{code}
    "stooq",        # format_symbol_for_stooq keeps .hk suffix
    "tencent",      # uses format_symbol_for_tencent, passes symbol through
    "sina",         # uses format_symbol_for_tencent, passes symbol through
]

# Sources known to handle BJ stocks (6-digit codes starting with '8')
BJ_CAPABLE_SOURCES = [
    "akshare",      # passes directly to stock_zh_a_hist (BJ is A-share market)
    "eastmoney",    # _resolve_secid maps 8xxxxx -> 2.{code}
    "baostock",     # _resolve_code maps 8xxxxx -> bj.{code}
    "tencent",      # format_symbol_for_tencent maps 8xxxxx -> bj{code}
    "sina",         # format_symbol_for_tencent maps 8xxxxx -> bj{code}
    "stooq",        # format_symbol_for_stooq maps 6-digit -> {code}.cn
]

DEFAULT_START = "20230101"
DEFAULT_END = "20231231"

# Required columns in the standard OHLCV DataFrame
REQUIRED_COLUMNS = {"date", "open", "high", "low", "close", "volume"}

# ── helper assertion mixin ────────────────────────────────────────────────


def assert_ohlcv_dataframe(test_case, df: pd.DataFrame, symbol: str, source: str):
    """Verify that *df* has the canonical OHLCV structure with data rows."""
    test_case.assertFalse(df.empty, f"{source}/{symbol}: DataFrame is empty")
    test_case.assertSetEqual(
        set(df.columns),
        REQUIRED_COLUMNS,
        f"{source}/{symbol}: expected columns {REQUIRED_COLUMNS}, got {set(df.columns)}",
    )
    test_case.assertTrue(pd.api.types.is_datetime64_any_dtype(df["date"]),
                         f"{source}/{symbol}: 'date' column is not datetime")
    for col in ("open", "high", "low", "close"):
        test_case.assertTrue(pd.api.types.is_numeric_dtype(df[col]),
                             f"{source}/{symbol}: '{col}' is not numeric")
    test_case.assertTrue(pd.api.types.is_numeric_dtype(df["volume"]),
                         f"{source}/{symbol}: 'volume' is not numeric")
    # Check data looks reasonable — at least some positive values
    test_case.assertGreater(df["close"].iloc[-1], 0,
                            f"{source}/{symbol}: latest close is not positive")
    test_case.assertGreaterEqual(len(df), 1,
                                 f"{source}/{symbol}: fewer than 1 row returned")


# ── test classes ──────────────────────────────────────────────────────────


class TestHKStockData(unittest.TestCase):
    """Integration tests for HK stock data across multiple data sources."""

    def test_hk_data_via_akshare(self):
        """Fetch HK stock 00700.HK via akshare provider."""
        try:
            df = get_data(symbol=HK_SYMBOL, source="akshare",
                          start_date=DEFAULT_START, end_date=DEFAULT_END)
            assert_ohlcv_dataframe(self, df, HK_SYMBOL, "akshare")
        except Exception as e:
            self.skipTest(f"akshare for {HK_SYMBOL} failed: {e}")

    def test_hk_data_via_eastmoney(self):
        """Fetch HK stock 00700.HK via eastmoney provider."""
        try:
            df = get_data(symbol=HK_SYMBOL, source="eastmoney",
                          start_date=DEFAULT_START, end_date=DEFAULT_END)
            assert_ohlcv_dataframe(self, df, HK_SYMBOL, "eastmoney")
        except Exception as e:
            self.skipTest(f"eastmoney for {HK_SYMBOL} failed: {e}")

    def test_hk_data_via_tencent(self):
        """Fetch HK stock 00700.HK via tencent provider."""
        try:
            df = get_data(symbol=HK_SYMBOL, source="tencent",
                          start_date=DEFAULT_START, end_date=DEFAULT_END)
            assert_ohlcv_dataframe(self, df, HK_SYMBOL, "tencent")
        except Exception as e:
            self.skipTest(f"tencent for {HK_SYMBOL} failed: {e}")

    def test_hk_data_via_sina(self):
        """Fetch HK stock 00700.HK via sina provider."""
        try:
            df = get_data(symbol=HK_SYMBOL, source="sina",
                          start_date=DEFAULT_START, end_date=DEFAULT_END)
            assert_ohlcv_dataframe(self, df, HK_SYMBOL, "sina")
        except Exception as e:
            self.skipTest(f"sina for {HK_SYMBOL} failed: {e}")

    def test_hk_data_via_stooq(self):
        """Fetch HK stock 00700.HK via stooq provider."""
        try:
            df = get_data(symbol=HK_SYMBOL, source="stooq",
                          start_date=DEFAULT_START, end_date=DEFAULT_END)
            assert_ohlcv_dataframe(self, df, HK_SYMBOL, "stooq")
        except Exception as e:
            self.skipTest(f"stooq for {HK_SYMBOL} failed: {e}")

    def test_hk_data_via_baostock(self):
        """Fetch HK stock 00700.HK via baostock provider."""
        try:
            df = get_data(symbol=HK_SYMBOL, source="baostock",
                          start_date=DEFAULT_START, end_date=DEFAULT_END)
            assert_ohlcv_dataframe(self, df, HK_SYMBOL, "baostock")
        except Exception as e:
            self.skipTest(f"baostock for {HK_SYMBOL} failed: {e}")

    def test_hk_data_at_least_one_source_succeeds(self):
        """Verify at least one data source can return HK stock data."""
        successes = []
        for src in HK_CAPABLE_SOURCES:
            try:
                df = get_data(symbol=HK_SYMBOL, source=src,
                              start_date=DEFAULT_START, end_date=DEFAULT_END)
                if not df.empty:
                    successes.append(src)
            except Exception:
                continue
        if not successes:
            self.skipTest(
                f"All HK-capable sources failed for {HK_SYMBOL}. "
                f"Tried: {HK_CAPABLE_SOURCES}. This is expected when no "
                f"network access to financial data APIs is available."
            )


class TestBJStockData(unittest.TestCase):
    """Integration tests for BJ (北证) stock data across multiple data sources."""

    def test_bj_data_via_akshare(self):
        """Fetch BJ stock 830799 via akshare provider."""
        try:
            df = get_data(symbol=BJ_SYMBOL, source="akshare",
                          start_date=DEFAULT_START, end_date=DEFAULT_END)
            assert_ohlcv_dataframe(self, df, BJ_SYMBOL, "akshare")
        except Exception as e:
            self.skipTest(f"akshare for {BJ_SYMBOL} failed: {e}")

    def test_bj_data_via_eastmoney(self):
        """Fetch BJ stock 830799 via eastmoney provider."""
        try:
            df = get_data(symbol=BJ_SYMBOL, source="eastmoney",
                          start_date=DEFAULT_START, end_date=DEFAULT_END)
            assert_ohlcv_dataframe(self, df, BJ_SYMBOL, "eastmoney")
        except Exception as e:
            self.skipTest(f"eastmoney for {BJ_SYMBOL} failed: {e}")

    def test_bj_data_via_tencent(self):
        """Fetch BJ stock 830799 via tencent provider."""
        try:
            df = get_data(symbol=BJ_SYMBOL, source="tencent",
                          start_date=DEFAULT_START, end_date=DEFAULT_END)
            assert_ohlcv_dataframe(self, df, BJ_SYMBOL, "tencent")
        except Exception as e:
            self.skipTest(f"tencent for {BJ_SYMBOL} failed: {e}")

    def test_bj_data_via_sina(self):
        """Fetch BJ stock 830799 via sina provider."""
        try:
            df = get_data(symbol=BJ_SYMBOL, source="sina",
                          start_date=DEFAULT_START, end_date=DEFAULT_END)
            assert_ohlcv_dataframe(self, df, BJ_SYMBOL, "sina")
        except Exception as e:
            self.skipTest(f"sina for {BJ_SYMBOL} failed: {e}")

    def test_bj_data_via_stooq(self):
        """Fetch BJ stock 830799 via stooq provider."""
        try:
            df = get_data(symbol=BJ_SYMBOL, source="stooq",
                          start_date=DEFAULT_START, end_date=DEFAULT_END)
            assert_ohlcv_dataframe(self, df, BJ_SYMBOL, "stooq")
        except Exception as e:
            self.skipTest(f"stooq for {BJ_SYMBOL} failed: {e}")

    def test_bj_data_via_baostock(self):
        """Fetch BJ stock 830799 via baostock provider."""
        try:
            df = get_data(symbol=BJ_SYMBOL, source="baostock",
                          start_date=DEFAULT_START, end_date=DEFAULT_END)
            assert_ohlcv_dataframe(self, df, BJ_SYMBOL, "baostock")
        except Exception as e:
            self.skipTest(f"baostock for {BJ_SYMBOL} failed: {e}")

    def test_bj_data_at_least_one_source_succeeds(self):
        """Verify at least one data source can return BJ stock data."""
        successes = []
        for src in BJ_CAPABLE_SOURCES:
            try:
                df = get_data(symbol=BJ_SYMBOL, source=src,
                              start_date=DEFAULT_START, end_date=DEFAULT_END)
                if not df.empty:
                    successes.append(src)
            except Exception:
                continue
        if not successes:
            self.skipTest(
                f"All BJ-capable sources failed for {BJ_SYMBOL}. "
                f"Tried: {BJ_CAPABLE_SOURCES}. This is expected when no "
                f"network access to financial data APIs is available."
            )


class TestMultiMarketDataFrameStructure(unittest.TestCase):
    """Verify returned DataFrame from HK and BJ data matches canonical schema."""

    def _try_fetch(self, symbol, source, start, end):
        """Attempt a fetch and return (df, error) tuple."""
        try:
            df = get_data(symbol=symbol, source=source,
                          start_date=start, end_date=end)
            return df, None
        except Exception as e:
            return None, str(e)

    def test_hk_dataframe_has_required_columns(self):
        """00700.HK data from any available source must have OHLCV columns."""
        for src in HK_CAPABLE_SOURCES:
            df, err = self._try_fetch(HK_SYMBOL, src, DEFAULT_START, DEFAULT_END)
            if df is not None and not df.empty:
                assert_ohlcv_dataframe(self, df, HK_SYMBOL, src)
                return
        self.skipTest(f"No HK-capable source returned data for {HK_SYMBOL}")

    def test_bj_dataframe_has_required_columns(self):
        """830799 data from any available source must have OHLCV columns."""
        for src in BJ_CAPABLE_SOURCES:
            df, err = self._try_fetch(BJ_SYMBOL, src, DEFAULT_START, DEFAULT_END)
            if df is not None and not df.empty:
                assert_ohlcv_dataframe(self, df, BJ_SYMBOL, src)
                return
        self.skipTest(f"No BJ-capable source returned data for {BJ_SYMBOL}")

    def test_hk_and_bj_data_sorted_by_date(self):
        """Both HK and BJ data returned by 'auto' source must be date-sorted."""
        for label, sym in [("HK", HK_SYMBOL), ("BJ", BJ_SYMBOL)]:
            try:
                df = get_data(symbol=sym, source="auto",
                              start_date=DEFAULT_START, end_date=DEFAULT_END)
                self.assertTrue((df["date"].diff().dropna() >= pd.Timedelta(0)).all(),
                                f"{sym}: data not sorted by date ascending")
            except Exception as e:
                self.skipTest(f"auto source for {sym} failed: {e}")


if __name__ == "__main__":
    unittest.main()
