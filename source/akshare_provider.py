import time
import random
import requests
import pandas as pd
from .base_provider import BaseProvider

# 东方财富 API 返回空数据时的常见原因提示
_RATE_LIMIT_HINT = (
    "akshare（东方财富）接口返回空数据，可能原因：\n"
    "1. 请求频率过高（速率限制），建议降低请求频率或稍后重试；\n"
    "2. 当前网络环境无法访问东方财富服务器（如 CI/CD 环境）；\n"
    "3. 股票代码不存在或数据范围超出可用区间。\n"
    "提示：akshare/baostock 均为免费接口，不存在付费限制；"
    "若持续失败请使用 source='baostock' 或 source='auto' 自动切换数据源。"
)


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

        last_error: Exception | None = None
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
            except Exception as e:
                # 捕获网络错误（ConnectionError 等）及其他异常，记录后继续重试
                last_error = e
                time.sleep(1)
                continue
            finally:
                requests.Session = orig_session

            if df is None or df.empty:
                time.sleep(1)
                continue

            df = df[["日期", "开盘", "最高", "最低", "收盘", "成交量"]]
            df.columns = ["date", "open", "high", "low", "close", "volume"]
            df["date"] = pd.to_datetime(df["date"])
            return df

        if last_error is not None:
            raise RuntimeError(
                f"akshare 请求失败（{type(last_error).__name__}: {last_error}）。\n{_RATE_LIMIT_HINT}"
            ) from last_error
        raise RuntimeError(f"akshare: 重试后仍无数据返回。\n{_RATE_LIMIT_HINT}")
