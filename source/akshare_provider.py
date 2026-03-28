import time
import random
import requests
import pandas as pd
from .base_provider import BaseProvider


def _normalize_ohlcv(df: pd.DataFrame,
                     date_col: str,
                     open_col: str,
                     high_col: str,
                     low_col: str,
                     close_col: str,
                     volume_col: str | None = None) -> pd.DataFrame:
    """将不同接口返回的数据归一化为统一 OHLCV 结构。"""
    out = pd.DataFrame({
        "date": pd.to_datetime(df[date_col]),
        "open": pd.to_numeric(df[open_col], errors='coerce'),
        "high": pd.to_numeric(df[high_col], errors='coerce'),
        "low": pd.to_numeric(df[low_col], errors='coerce'),
        "close": pd.to_numeric(df[close_col], errors='coerce'),
    })
    if volume_col and volume_col in df.columns:
        out["volume"] = pd.to_numeric(df[volume_col], errors='coerce').fillna(0.0)
    else:
        out["volume"] = 0.0
    out = out.dropna(subset=["date", "open", "high", "low", "close"]).sort_values("date")
    return out.reset_index(drop=True)


def _filter_date_range(df: pd.DataFrame, start_date: str | None, end_date: str | None) -> pd.DataFrame:
    """按用户请求时间段过滤数据（支持 YYYYMMDD / YYYY-MM-DD）。"""
    out = df
    try:
        if start_date:
            out = out[out["date"] >= pd.to_datetime(start_date)]
        if end_date:
            out = out[out["date"] <= pd.to_datetime(end_date)]
    except Exception:
        return df
    return out.reset_index(drop=True)


class AkshareProvider(BaseProvider):
    def __init__(self, max_attempts: int = 3):
        self.max_attempts = max_attempts

    def fetch(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        # akshare 接口期望不带市场前缀，直接传入 symbol
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
        ]

        try:
            import akshare as ak
        except Exception as e:
            raise ImportError("akshare is required for AkshareProvider") from e

        def _fetch_stock_hist() -> pd.DataFrame:
            stock_df = ak.stock_zh_a_hist(symbol=symbol,
                                          period="daily",
                                          start_date=start_date,
                                          end_date=end_date,
                                          adjust="qfq",
                                          timeout=None)
            if stock_df is None or stock_df.empty:
                return pd.DataFrame()
            return _normalize_ohlcv(
                stock_df,
                date_col="日期",
                open_col="开盘",
                high_col="最高",
                low_col="最低",
                close_col="收盘",
                volume_col="成交量",
            )

        def _fetch_global_futures_hist() -> pd.DataFrame:
            futures_df = ak.futures_global_hist_em(symbol=symbol)
            if futures_df is None or futures_df.empty:
                return pd.DataFrame()
            return _normalize_ohlcv(
                futures_df,
                date_col="日期",
                open_col="开盘",
                high_col="最高",
                low_col="最低",
                close_col="最新价",
                volume_col="总量",
            )

        def _fetch_etf_hist() -> pd.DataFrame:
            etf_df = ak.fund_etf_hist_em(symbol=symbol,
                                         period="daily",
                                         start_date=start_date,
                                         end_date=end_date,
                                         adjust="")
            if etf_df is None or etf_df.empty:
                return pd.DataFrame()
            return _normalize_ohlcv(
                etf_df,
                date_col="日期",
                open_col="开盘",
                high_col="最高",
                low_col="最低",
                close_col="收盘",
                volume_col="成交量",
            )

        def _fetch_open_fund_nav() -> pd.DataFrame:
            nav_df = ak.fund_open_fund_info_em(fund=symbol, indicator="单位净值走势")
            if nav_df is None or nav_df.empty:
                return pd.DataFrame()

            date_col = "净值日期" if "净值日期" in nav_df.columns else "日期"
            value_col = "单位净值" if "单位净值" in nav_df.columns else None
            if value_col is None:
                return pd.DataFrame()

            norm_df = pd.DataFrame({
                "date": pd.to_datetime(nav_df[date_col]),
                "close": pd.to_numeric(nav_df[value_col], errors='coerce'),
            }).dropna(subset=["date", "close"])
            if norm_df.empty:
                return pd.DataFrame()

            # 场外基金净值没有日内 OHLC，这里用单位净值回填，满足统一回测接口。
            norm_df["open"] = norm_df["close"]
            norm_df["high"] = norm_df["close"]
            norm_df["low"] = norm_df["close"]
            norm_df["volume"] = 0.0
            return norm_df[["date", "open", "high", "low", "close", "volume"]].sort_values("date").reset_index(drop=True)

        fetchers = []
        if any(ch.isalpha() for ch in symbol):
            fetchers.append(_fetch_global_futures_hist)
        fetchers.extend((_fetch_stock_hist, _fetch_etf_hist, _fetch_open_fund_nav))

        for attempt in range(1, self.max_attempts + 1):
            sess = requests.Session()
            sess.headers.update({"User-Agent": random.choice(user_agents)})
            orig_session = requests.Session
            requests.Session = lambda *a, **k: sess

            try:
                for fetcher in fetchers:
                    try:
                        df = fetcher()
                        if df is not None and not df.empty:
                            return _filter_date_range(df, start_date=start_date, end_date=end_date)
                    except Exception:
                        continue
            finally:
                requests.Session = orig_session

            time.sleep(1)

        raise RuntimeError("akshare: no stock/etf/open-fund data returned after retries")
