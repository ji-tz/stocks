import os
import time
import random
import requests
import pandas as pd

# 在模块级尝试导入 akshare/baostock，便于测试时 patch
try:
    import akshare as ak
except Exception:
    ak = None

try:
    import baostock as bs
except Exception:
    bs = None

def _ensure_cache_dir(cache_dir: str):
    os.makedirs(cache_dir, exist_ok=True)

def _save_cache(df: pd.DataFrame, cache_file: str):
    try:
        df.to_csv(cache_file, index=False)
    except Exception:
        pass

def get_data(symbol: str = "600900",
             source: str = "akshare",
             start_date: str = "19700101",
             end_date: str = "20500101",
             cache_dir: str = "data",
             max_attempts: int = 3) -> pd.DataFrame:
    """
    获取日线数据的统一接口。

    参数:
      - symbol: 股票代码（例如 '600900'）
      - source: 'akshare' 或 'baostock'
      - start_date/end_date: akshare 使用 YYYYMMDD，baostock 使用 YYYY-MM-DD
      - cache_dir: 本地缓存目录
      - max_attempts: akshare 重试次数

    返回 DataFrame，列为 ['date','open','high','low','close','volume']，且 `date` 为 datetime。
    """
    _ensure_cache_dir(cache_dir)
    cache_file = os.path.join(cache_dir, f"{symbol}.csv")

    source = (source or "").lower()
    if source == "akshare":
        try:
            import akshare as ak
        except Exception as e:
            raise ImportError("akshare is required for source='akshare'") from e

        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
        ]

        for attempt in range(1, max_attempts + 1):
            sess = requests.Session()
            sess.headers.update({"User-Agent": random.choice(user_agents)})
            orig_session = requests.Session
            requests.Session = lambda *a, **k: sess

            try:
                df = ak.stock_zh_a_hist(symbol=symbol,
                                        period="daily",
                                        start_date=start_date,
                                        end_date=end_date,
                                        adjust="",
                                        timeout=None)
            finally:
                requests.Session = orig_session

            if df is None or df.empty:
                # 若失败则尝试下一次
                time.sleep(1)
                continue

            df = df[["日期", "开盘", "最高", "最低", "收盘", "成交量"]]
            df.columns = ["date", "open", "high", "low", "close", "volume"]
            df["date"] = pd.to_datetime(df["date"])
            _save_cache(df, cache_file)
            return df

        # 回退到本地缓存（如果存在）
        if os.path.exists(cache_file):
            return pd.read_csv(cache_file, parse_dates=["date"]).loc[:, ["date", "open", "high", "low", "close", "volume"]]

        raise RuntimeError("akshare 获取数据失败且无本地缓存")

    elif source == "baostock":
        try:
            import baostock as bs
        except Exception as e:
            raise ImportError("baostock 未安装。请先 `pip install baostock` 后重试。") from e

        # baostock 要求带市场前缀，例如 'sh.600900' 或 'sz.000001'
        if symbol.startswith("6"):
            code = f"sh.{symbol}"
        else:
            code = f"sz.{symbol}"

        lg = bs.login()
        if lg.error_code != "0":
            bs.logout()
            raise RuntimeError("baostock 登录失败")

        # baostock 使用 YYYY-MM-DD
        sd = start_date if "-" in start_date else f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
        ed = end_date if "-" in end_date else f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"

        rs = bs.query_history_k_data_plus(code,
                                          "date,open,high,low,close,volume",
                                          start_date=sd,
                                          end_date=ed,
                                          frequency="d",
                                          adjustflag="3")

        if rs.error_code != "0":
            bs.logout()
            raise RuntimeError(f"baostock 查询失败: {rs.error_msg}")

        data_list = []
        while rs.next():
            data_list.append(rs.get_row_data())

        bs.logout()

        if not data_list:
            if os.path.exists(cache_file):
                return pd.read_csv(cache_file, parse_dates=["date"]).loc[:, ["date", "open", "high", "low", "close", "volume"]]
            raise RuntimeError("baostock 未返回数据且无本地缓存")

        df = pd.DataFrame(data_list, columns=rs.fields)
        df = df.rename(columns={"date": "date", "open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"})
        df["date"] = pd.to_datetime(df["date"])
        # 将数值列转换为数值类型
        for c in ["open", "high", "low", "close", "volume"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        _save_cache(df, cache_file)
        return df.loc[:, ["date", "open", "high", "low", "close", "volume"]]

    else:
        raise ValueError(f"不支持的数据源: {source}")
