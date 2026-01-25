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
        # 原子替换：先写入临时文件，再用 os.replace 原子替换目标文件
        dirpath = os.path.dirname(cache_file) or "."
        os.makedirs(dirpath, exist_ok=True)
        tmp_file = cache_file + ".tmp"
        df.to_csv(tmp_file, index=False)
        try:
            os.replace(tmp_file, cache_file)
        except Exception:
            # 在某些文件系统上 os.replace 可能失败，回退到写入直接覆盖
            try:
                df.to_csv(cache_file, index=False)
            except Exception:
                pass
    except Exception:
        pass

def get_data(symbol: str = "600900",
             source: object = "akshare",
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

    # 支持传入单个 source（字符串），或多个 source（列表/元组），或 'auto' 自动尝试常见来源
    if not source:
        source = "auto"

    if isinstance(source, (list, tuple)):
        sources = [s.lower() for s in source]
    elif isinstance(source, str):
        s = source.lower()
        if s == "auto":
            sources = ["akshare", "baostock"]
        else:
            sources = [s]
    else:
        raise ValueError("source must be a string or list/tuple of strings")

    errors = []
    for src in sources:
        try:
            if src == "akshare":
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
                        time.sleep(1)
                        continue

                    df = df[["日期", "开盘", "最高", "最低", "收盘", "成交量"]]
                    df.columns = ["date", "open", "high", "low", "close", "volume"]
                    df["date"] = pd.to_datetime(df["date"])
                    _save_cache(df, cache_file)
                    return df

                errors.append(("akshare", "no data returned"))

            elif src == "baostock":
                try:
                    import baostock as bs
                except Exception as e:
                    raise ImportError("baostock 未安装。请先 `pip install baostock` 后重试。") from e

                if symbol.startswith("6"):
                    code = f"sh.{symbol}"
                else:
                    code = f"sz.{symbol}"

                lg = bs.login()
                if lg.error_code != "0":
                    bs.logout()
                    raise RuntimeError("baostock 登录失败")

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
                    errors.append(("baostock", "no data returned"))
                else:
                    df = pd.DataFrame(data_list, columns=rs.fields)
                    df = df.rename(columns={"date": "date", "open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"})
                    df["date"] = pd.to_datetime(df["date"])
                    for c in ["open", "high", "low", "close", "volume"]:
                        df[c] = pd.to_numeric(df[c], errors="coerce")

                    _save_cache(df, cache_file)
                    return df.loc[:, ["date", "open", "high", "low", "close", "volume"]]

            else:
                errors.append((src, "unsupported source"))

        except Exception as e:
            # 捕捉单个数据源的异常并继续尝试下一个
            errors.append((src, str(e)))
            continue

    # 所有 source 均尝试过且未返回数据则尝试本地缓存
    if os.path.exists(cache_file):
        try:
            return pd.read_csv(cache_file, parse_dates=["date"]).loc[:, ["date", "open", "high", "low", "close", "volume"]]
        except Exception:
            pass

    # 汇总错误信息并抛出
    msg = "; ".join([f"{s}: {err}" for s, err in errors]) if errors else "unknown error"
    raise RuntimeError(f"所有数据源均失败: {msg}")
