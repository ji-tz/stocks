import time
import random
import requests
import pandas as pd
from .base_provider import BaseProvider


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

        for attempt in range(1, self.max_attempts + 1):
            sess = requests.Session()
            sess.headers.update({"User-Agent": random.choice(user_agents)})
            orig_session = requests.Session
            requests.Session = lambda *a, **k: sess

            try:
                df = ak.stock_zh_a_hist(symbol=symbol,
                                        period="daily",
                                        start_date=start_date,
                                        end_date=end_date,
                                        adjust="qfq",
                                        timeout=None)
            finally:
                requests.Session = orig_session

            if df is None or df.empty:
                time.sleep(1)
                continue

            df = df[["日期", "开盘", "最高", "最低", "收盘", "成交量"]]
            df.columns = ["date", "open", "high", "low", "close", "volume"]
            df["date"] = pd.to_datetime(df["date"])
            return df

        raise RuntimeError("akshare: no data returned after retries")
