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

from .akshare_provider import AkshareProvider
from .baostock_provider import BaostockProvider


DEFAULT_FETCH_BUFFER_DAYS = 5

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


def _parse_date_input(value: str | None):
    """将用户输入日期解析为 pandas 时间。"""
    if value is None:
        return None
    value = str(value).strip()
    if value == "":
        return None
    import re
    if re.fullmatch(r"\d{8}", value):
        return pd.to_datetime(value, format="%Y%m%d")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return pd.to_datetime(value, format="%Y-%m-%d")
    return pd.to_datetime(value)


def _format_date_for_source(value, source_name: str) -> str | None:
    """按数据源要求输出日期格式。"""
    if value is None:
        return None
    timestamp = pd.to_datetime(value)
    if source_name == 'baostock':
        return timestamp.strftime('%Y-%m-%d')
    return timestamp.strftime('%Y%m%d')


def _expand_fetch_range(start_date: str | None,
                        end_date: str | None,
                        buffer_days: int) -> tuple[str | None, str | None]:
    """按配置为下载请求扩展前后缓冲天数。"""
    start_dt = _parse_date_input(start_date)
    end_dt = _parse_date_input(end_date)

    if buffer_days <= 0:
        return start_date, end_date

    if start_dt is not None:
        start_dt = start_dt - pd.Timedelta(days=buffer_days)
    if end_dt is not None:
        end_dt = end_dt + pd.Timedelta(days=buffer_days)

    return (
        _format_date_for_source(start_dt, 'baostock' if isinstance(start_date, str) and '-' in start_date else 'akshare') if start_dt is not None else start_date,
        _format_date_for_source(end_dt, 'baostock' if isinstance(end_date, str) and '-' in end_date else 'akshare') if end_dt is not None else end_date,
    )


def _read_cache_raw(cache_file: str) -> pd.DataFrame | None:
    """读取完整缓存，不做时间裁剪。"""
    if not os.path.exists(cache_file):
        return None
    try:
        cached = pd.read_csv(cache_file, parse_dates=["date"])
        req_cols = ["date", "open", "high", "low", "close", "volume"]
        if not set(req_cols).issubset(cached.columns):
            return None
        return cached.loc[:, req_cols].sort_values('date').reset_index(drop=True)
    except Exception:
        return None


def _read_cache(cache_file: str, start_date: str | None = None, end_date: str | None = None) -> pd.DataFrame | None:
    """Read cache file and optionally filter by start/end (supports YYYYMMDD and YYYY-MM-DD).

    Returns filtered DataFrame or None if cache not present or invalid.
    """
    cached = _read_cache_raw(cache_file)
    if cached is None:
        return None

    try:
        sd = _parse_date_input(start_date)
        ed = _parse_date_input(end_date)
        out = cached
        if sd is not None:
            out = out[out['date'] >= sd]
        if ed is not None:
            out = out[out['date'] <= ed]
        return out
    except Exception:
        return None


def _merge_into_cache(cache_file: str, df_new: pd.DataFrame) -> None:
    """Merge df_new into existing cache file (by `date`), deduplicate, sort and save atomically.

    If cache doesn't exist, simply save df_new.
    """
    try:
        # Ensure date column is datetime and consistent
        df_new = df_new.copy()
        df_new['date'] = pd.to_datetime(df_new['date'])
        if os.path.exists(cache_file):
            try:
                existing = pd.read_csv(cache_file, parse_dates=['date'])
                # concat and drop duplicates by date keeping last (newer)
                merged = pd.concat([existing, df_new], ignore_index=True)
                merged = merged.drop_duplicates(subset=['date'], keep='last')
                merged = merged.sort_values('date').reset_index(drop=True)
                _save_cache(merged, cache_file)
                return
            except Exception:
                # fallback to overwrite
                _save_cache(df_new.sort_values('date').reset_index(drop=True), cache_file)
                return
        else:
            _save_cache(df_new.sort_values('date').reset_index(drop=True), cache_file)
    except Exception:
        # best-effort: do nothing on failure
        pass

def get_data(symbol: str = "600900",
             source: object = "akshare",
             start_date: str = "19700101",
             end_date: str = "20500101",
             cache_dir: str = "data",
             max_attempts: int = 3,
             force_refresh: bool = False,
             buffer_days: int = DEFAULT_FETCH_BUFFER_DAYS) -> pd.DataFrame:
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

    # 优先尝试从缓存读取（并按时间范围过滤）。使用抽象化函数以便复用。
    cached_out = _read_cache(cache_file, start_date=start_date, end_date=end_date)
    cached_raw = _read_cache_raw(cache_file)
    if not force_refresh and cached_out is not None:
        # 如果请求了具体区间，且缓存能覆盖该区间（包含边界），直接返回
        try:
            if start_date or end_date:
                # 判断缓存覆盖情况
                if cached_raw is not None and not cached_raw.empty:
                    min_dt = cached_raw['date'].min()
                    max_dt = cached_raw['date'].max()
                    ok_start = True
                    ok_end = True
                    if start_date:
                        sd = _parse_date_input(start_date)
                        ok_start = (min_dt <= sd)
                    if end_date:
                        ed = _parse_date_input(end_date)
                        ok_end = (max_dt >= ed)
                    if ok_start and ok_end:
                        return cached_out
            else:
                # 没有指定日期，直接返回缓存
                return cached_out
        except Exception:
            # 若校验覆盖范围失败，继续走 provider 流程
            pass

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
    # 使用多态 provider 实现
    provider_map = {
        "akshare": lambda: AkshareProvider(max_attempts=max_attempts),
        "baostock": lambda: BaostockProvider(),
    }

    for src in sources:
        src = src.lower()
        if src not in provider_map:
            errors.append((src, "unsupported source"))
            continue

        provider = provider_map[src]()
        try:
            fetch_start = start_date
            fetch_end = end_date
            if start_date or end_date:
                request_start, request_end = _expand_fetch_range(start_date, end_date, buffer_days)
                fetch_start = _format_date_for_source(_parse_date_input(request_start), src) if request_start else request_start
                fetch_end = _format_date_for_source(_parse_date_input(request_end), src) if request_end else request_end

            df = provider.fetch(symbol=symbol, start_date=fetch_start, end_date=fetch_end)
            if df is None or df.empty:
                errors.append((src, "no data returned"))
                continue

            # 将新拉取的数据合并入缓存（去重并排序）
            _merge_into_cache(cache_file, df)

            # 从缓存读取并按请求的时间范围返回（以保证一致性）
            cached_after = _read_cache(cache_file, start_date=start_date, end_date=end_date)
            if cached_after is not None:
                return cached_after
            return df
        except Exception as e:
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
