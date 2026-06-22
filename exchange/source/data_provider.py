import os
import logging
import pandas as pd

logger = logging.getLogger(__name__)

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
from .stooq_provider import StooqProvider
from .tencent_provider import TencentProvider
from .sina_provider import SinaProvider
from .sohu_provider import SohuProvider
from .eastmoney_provider import EastmoneyProvider
from .cailianpress_provider import CailianpressProvider

from .provider_utils import (
    parse_date_input,
    format_date_for_source,
    format_symbol_for_tencent,
    format_symbol_for_stooq,
    parse_jsonp,
    filter_by_optional_range,
)

_parse_date_input = parse_date_input
_format_date_for_source = format_date_for_source
_format_symbol_for_tencent = format_symbol_for_tencent
_format_symbol_for_stooq = format_symbol_for_stooq
_parse_jsonp = parse_jsonp
_filter_by_optional_range = filter_by_optional_range


DEFAULT_FETCH_BUFFER_DAYS = 1


def _ensure_cache_dir(cache_dir: str):
    os.makedirs(cache_dir, exist_ok=True)


def _save_cache(df: pd.DataFrame, cache_file: str):
    try:
        dirpath = os.path.dirname(cache_file) or "."
        os.makedirs(dirpath, exist_ok=True)
        tmp_file = cache_file + ".tmp"
        df.to_csv(tmp_file, index=False)
        try:
            os.replace(tmp_file, cache_file)
        except OSError:
            logger.warning("缓存文件原子替换失败，尝试直接写入")
            try:
                df.to_csv(cache_file, index=False)
            except OSError:
                logger.warning("缓存文件直接写入也失败")
    except Exception:
        logger.warning("缓存保存异常", exc_info=True)


def _expand_fetch_range(start_date: str | None,
                        end_date: str | None,
                        buffer_days: int) -> tuple[str | None, str | None]:
    start_dt = parse_date_input(start_date)
    end_dt = parse_date_input(end_date)

    if buffer_days <= 0:
        return start_date, end_date

    if start_dt is not None:
        start_dt = start_dt - pd.Timedelta(days=buffer_days)
    if end_dt is not None:
        end_dt = end_dt + pd.Timedelta(days=buffer_days)

    fmt = 'baostock' if isinstance(start_date, str) and '-' in (start_date or '') else 'akshare'
    return (
        format_date_for_source(start_dt, fmt) if start_dt is not None else start_date,
        format_date_for_source(end_dt, fmt) if end_dt is not None else end_date,
    )


def _read_cache_raw(cache_file: str) -> pd.DataFrame | None:
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
    cached = _read_cache_raw(cache_file)
    if cached is None:
        return None

    try:
        sd = parse_date_input(start_date)
        ed = parse_date_input(end_date)
        out = cached
        if sd is not None:
            out = out[out['date'] >= sd]
        if ed is not None:
            out = out[out['date'] <= ed]
        return out
    except Exception:
        return None


def _merge_into_cache(cache_file: str, df_new: pd.DataFrame) -> None:
    try:
        df_new = df_new.copy()
        df_new['date'] = pd.to_datetime(df_new['date'])
        if os.path.exists(cache_file):
            try:
                existing = pd.read_csv(cache_file, parse_dates=['date'])
                merged = pd.concat([existing, df_new], ignore_index=True)
                merged = merged.drop_duplicates(subset=['date'], keep='last')
                merged = merged.sort_values('date').reset_index(drop=True)
                _save_cache(merged, cache_file)
                return
            except Exception:
                _save_cache(df_new.sort_values('date').reset_index(drop=True), cache_file)
                return
        else:
            _save_cache(df_new.sort_values('date').reset_index(drop=True), cache_file)
    except Exception:
        logger.warning("缓存合并失败: %s", cache_file)


def _determine_missing_ranges(
    cached_df: pd.DataFrame | None,
    start_date: str | None,
    end_date: str | None,
) -> list[tuple[str | None, str | None]]:
    """Determine which date ranges are missing from the cache.

    Returns a list of (fetch_start, fetch_end) tuples for the missing portions.
    """
    sd = parse_date_input(start_date)
    ed = parse_date_input(end_date)

    if sd is None and ed is None:
        # No range specified — only missing if cache is empty
        return [(start_date, end_date)] if cached_df is None or cached_df.empty else []

    if cached_df is None or cached_df.empty:
        return [(start_date, end_date)]

    cache_min = cached_df['date'].min()
    cache_max = cached_df['date'].max()

    ranges = []

    # Missing at the beginning
    if sd is not None and sd < cache_min:
        miss_end = format_date_for_source(cache_min - pd.Timedelta(days=1), 'akshare')
        fmt_start = format_date_for_source(sd, 'akshare')
        ranges.append((fmt_start, miss_end))

    # Missing at the end
    if ed is not None and ed > cache_max:
        miss_start = format_date_for_source(cache_max + pd.Timedelta(days=1), 'akshare')
        fmt_end = format_date_for_source(ed, 'akshare')
        ranges.append((miss_start, fmt_end))

    return ranges


_PROVIDER_FACTORIES = {
    "akshare": lambda: AkshareProvider(max_attempts=3),
    "baostock": lambda: BaostockProvider(),
    "tencent": lambda: TencentProvider(),
    "sina": lambda: SinaProvider(),
    "sohu": lambda: SohuProvider(),
    "eastmoney": lambda: EastmoneyProvider(),
    "cailianpress": lambda: CailianpressProvider(),
    "stooq": lambda: StooqProvider(),
}

ALL_SOURCES = list(_PROVIDER_FACTORIES.keys())

# When cache is mostly present and only a small date gap (< 3 days) needs filling,
# only try the fastest sources instead of the full 8-source auto traversal.
# This avoids timeout stacking from slow/specialized sources.
_CACHE_GAP_FAST_SOURCES = ALL_SOURCES[:3]  # akshare, baostock, tencent


def _create_provider(source_name: str, max_attempts: int = 3):
    src = source_name.lower()
    factory = _PROVIDER_FACTORIES.get(src)
    if factory is None:
        raise ValueError(f"unsupported source: {source_name}")
    if src == "akshare":
        return AkshareProvider(max_attempts=max_attempts)
    return factory()


def get_data(symbol: str = "600900",
             source: object = "akshare",
             start_date: str = "19700101",
             end_date: str = "20500101",
             cache_dir: str = "data",
             max_attempts: int = 3,
             force_refresh: bool = False,
             buffer_days: int = DEFAULT_FETCH_BUFFER_DAYS) -> pd.DataFrame:
    """获取股票行情数据，实现 Cache-First 策略。

    Cache-First 流程:
    1. 检查 data/{symbol}.csv 缓存是否存在
    2. 如果缓存覆盖请求范围（且不含实时今天数据），直接返回缓存（cache hit）
    3. 如果缓存仅部分覆盖，只抓取缺失部分并合并（partial cache）
    4. 如果 force_refresh=True 或含当天实时数据，跳过缓存直接抓取
    """
    _ensure_cache_dir(cache_dir)
    cache_file = os.path.join(cache_dir, f"{symbol}.csv")

    today = pd.Timestamp.now().normalize()
    sd = parse_date_input(start_date)
    ed = parse_date_input(end_date)

    # Determine if today's real-time data is needed (used both in and after cache logic)
    needs_realtime = ed is not None and ed >= today

    # --- Cache-First Strategy ---
    if not force_refresh:
        cached_raw = _read_cache_raw(cache_file)
        if cached_raw is not None and not cached_raw.empty:
            cache_min = cached_raw['date'].min()
            cache_max = cached_raw['date'].max()

            if needs_realtime:
                # For real-time: historical portion can still come from cache
                hist_end = today - pd.Timedelta(days=1)
                hist_covered = True
                if sd is not None and sd < cache_min:
                    hist_covered = False
                if hist_end > cache_max:
                    hist_covered = False

                if hist_covered and (sd is None or sd <= cache_max):
                    # Historical data is cached; will fetch only today's data
                    logger.info(
                        "缓存命中(historical), 需补充实时数据: symbol=%s, "
                        "cached=%s~%s, today=%s",
                        symbol, cache_min.date(), cache_max.date(), today.date(),
                    )
                else:
                    # Partial cache + realtime — log and proceed to fetch
                    logger.info(
                        "缓存部分命中+需实时数据: symbol=%s, "
                        "cached=%s~%s, requested=%s~%s",
                        symbol, cache_min.date(), cache_max.date(),
                        start_date or "N/A", end_date or "N/A",
                    )
            else:
                # Pure historical request — check if cache fully covers
                hist_covered = True
                if sd is not None and sd < cache_min:
                    hist_covered = False
                if ed is not None and ed > cache_max + pd.Timedelta(days=buffer_days):
                    hist_covered = False

                if hist_covered:
                    cached_out = _read_cache(cache_file, start_date=start_date, end_date=end_date)
                    if cached_out is not None and not cached_out.empty:
                        logger.info(
                            "缓存命中: symbol=%s, range=%s~%s, rows=%d",
                            symbol, start_date or "N/A", end_date or "N/A", len(cached_out),
                        )
                        return cached_out
                else:
                    logger.info(
                        "缓存部分命中: symbol=%s, cached=%s~%s, requested=%s~%s",
                        symbol, cache_min.date(), cache_max.date(),
                        start_date or "N/A", end_date or "N/A",
                    )
        else:
            logger.info("缓存未命中: symbol=%s, cache=%s", symbol, cache_file)
    else:
        logger.info("强制刷新缓存: symbol=%s, cache=%s", symbol, cache_file)

    # --- Source resolution ---
    if not source:
        source = "auto"

    if isinstance(source, (list, tuple)):
        sources = [s.lower() for s in source]
    elif isinstance(source, str):
        s = source.lower()
        if s == "auto":
            sources = ALL_SOURCES.copy()
        else:
            sources = [s]
    else:
        raise ValueError("source must be a string or list/tuple of strings")

    # --- Determine what needs to be fetched ---
    # If we have partial cache, determine missing ranges
    if not force_refresh:
        cached_raw = _read_cache_raw(cache_file)
        missing_ranges = _determine_missing_ranges(cached_raw, start_date, end_date)
    else:
        missing_ranges = [(start_date, end_date)] if start_date or end_date else [(None, None)]

    # Also need to consider real-time today data
    if not force_refresh and needs_realtime:
        today_str = format_date_for_source(today, 'akshare')
        # Only add today if not already covered in missing ranges
        already_missing_today = any(
            (fs is None or fs <= today_str) and (fe is None or fe >= today_str)
            for fs, fe in missing_ranges
        )
        if not already_missing_today:
            missing_ranges.append((today_str, today_str))

    # --- Optimize: for small cache gaps, limit source fallback ---
    # When cache exists and only a few days are missing, don't traverse all 8 sources.
    # Try the top-3 fastest sources only (akshare, baostock, tencent).
    if (not force_refresh
            and cached_raw is not None
            and not cached_raw.empty
            and len(sources) >= 4):
        total_gap_days = 0
        for fs, fe in missing_ranges:
            if fs and fe:
                fs_dt = parse_date_input(fs)
                fe_dt = parse_date_input(fe)
                if fs_dt is not None and fe_dt is not None:
                    total_gap_days += (fe_dt - fs_dt).days
        if 0 <= total_gap_days <= 3:
            logger.info(
                "缓存小缺口(%d天), 限制源为快速源: symbol=%s, %s",
                total_gap_days, symbol, _CACHE_GAP_FAST_SOURCES,
            )
            sources = _CACHE_GAP_FAST_SOURCES

    errors = []

    for fetch_start, fetch_end in missing_ranges:
        for src in sources:
            src = src.lower()
            if src not in _PROVIDER_FACTORIES:
                errors.append((src, "unsupported source"))
                continue

            try:
                f_start = fetch_start
                f_end = fetch_end

                # Apply buffer only for non-realtime (today) fetches
                if fetch_start and fetch_end:
                    f_start_dt = parse_date_input(fetch_start)
                    f_end_dt = parse_date_input(fetch_end)
                    is_today_fetch = (
                        f_end_dt is not None
                        and f_start_dt is not None
                        and f_start_dt == f_end_dt
                        and f_start_dt == today
                    )
                    if not is_today_fetch:
                        request_start, request_end = _expand_fetch_range(
                            fetch_start, fetch_end, buffer_days
                        )
                        f_start = format_date_for_source(
                            parse_date_input(request_start), src
                        ) if request_start else request_start
                        f_end = format_date_for_source(
                            parse_date_input(request_end), src
                        ) if request_end else request_end
                    else:
                        # For today's data, no buffer needed
                        f_start = format_date_for_source(
                            parse_date_input(fetch_start), src
                        ) if fetch_start else fetch_start
                        f_end = format_date_for_source(
                            parse_date_input(fetch_end), src
                        ) if fetch_end else fetch_end
                else:
                    f_start = fetch_start
                    f_end = fetch_end

                provider = _create_provider(src, max_attempts=max_attempts)
                df = provider.fetch(
                    symbol=symbol, start_date=f_start, end_date=f_end
                )

                if df is None or df.empty:
                    errors.append((src, f"no data returned for {fetch_start}~{fetch_end}"))
                    continue

                _merge_into_cache(cache_file, df)
                break  # Success with this source, move to next missing range

            except Exception as e:
                errors.append((src, str(e)))
                continue

    # --- Return result ---
    cached_out = _read_cache(cache_file, start_date=start_date, end_date=end_date)
    if cached_out is not None and not cached_out.empty:
        return cached_out

    # Fallback: try to return whatever is in cache
    if os.path.exists(cache_file):
        try:
            return pd.read_csv(cache_file, parse_dates=["date"]).loc[:, [
                "date", "open", "high", "low", "close", "volume"]]
        except Exception:
            logger.warning("缓存回退读取失败: %s", cache_file)

    msg = "; ".join([f"{s}: {err}" for s, err in errors]) if errors else "unknown error"
    raise RuntimeError(f"所有数据源均失败: {msg}")
