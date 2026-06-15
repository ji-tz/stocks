import os
import pandas as pd

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


DEFAULT_FETCH_BUFFER_DAYS = 5


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
            try:
                df.to_csv(cache_file, index=False)
            except OSError:
                pass
    except Exception:
        pass


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
        pass


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
    _ensure_cache_dir(cache_dir)
    cache_file = os.path.join(cache_dir, f"{symbol}.csv")

    cached_out = _read_cache(cache_file, start_date=start_date, end_date=end_date)
    cached_raw = _read_cache_raw(cache_file)
    if not force_refresh and cached_out is not None:
        try:
            if start_date or end_date:
                if cached_raw is not None and not cached_raw.empty:
                    min_dt = cached_raw['date'].min()
                    max_dt = cached_raw['date'].max()
                    ok_start = True
                    ok_end = True
                    if start_date:
                        sd = parse_date_input(start_date)
                        ok_start = (min_dt <= sd)
                    if end_date:
                        ed = parse_date_input(end_date)
                        ok_end = (max_dt >= ed)
                    if ok_start and ok_end:
                        return cached_out
            else:
                return cached_out
        except Exception:
            pass

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

    errors = []

    for src in sources:
        src = src.lower()
        if src not in _PROVIDER_FACTORIES:
            errors.append((src, "unsupported source"))
            continue

        try:
            fetch_start = start_date
            fetch_end = end_date
            if start_date or end_date:
                request_start, request_end = _expand_fetch_range(start_date, end_date, buffer_days)
                fetch_start = format_date_for_source(parse_date_input(request_start), src) if request_start else request_start
                fetch_end = format_date_for_source(parse_date_input(request_end), src) if request_end else request_end

            provider = _create_provider(src, max_attempts=max_attempts)
            df = provider.fetch(symbol=symbol, start_date=fetch_start, end_date=fetch_end)

            if df is None or df.empty:
                errors.append((src, "no data returned"))
                continue

            _merge_into_cache(cache_file, df)

            cached_after = _read_cache(cache_file, start_date=start_date, end_date=end_date)
            if cached_after is not None:
                return cached_after
            return df
        except Exception as e:
            errors.append((src, str(e)))
            continue

    if os.path.exists(cache_file):
        try:
            return pd.read_csv(cache_file, parse_dates=["date"]).loc[:, ["date", "open", "high", "low", "close", "volume"]]
        except Exception:
            pass

    msg = "; ".join([f"{s}: {err}" for s, err in errors]) if errors else "unknown error"
    raise RuntimeError(f"所有数据源均失败: {msg}")
