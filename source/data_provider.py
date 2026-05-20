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


def _format_symbol_for_stooq(symbol: str) -> str:
    """将本地代码转换为 stooq 所需代码。"""
    normalized = str(symbol).strip().lower()
    if '.' in normalized:
        return normalized
    # A股在 stooq 通常使用 .cn 后缀，例如 600900.cn
    if normalized.isdigit() and len(normalized) == 6:
        return f"{normalized}.cn"
    return normalized


def _fetch_from_stooq(symbol: str, start_date: str | None, end_date: str | None) -> pd.DataFrame:
    """从 stooq 拉取日线 OHLCV 数据并标准化。"""
    stooq_symbol = _format_symbol_for_stooq(symbol)
    url = f"https://stooq.com/q/d/l/?s={stooq_symbol}&i=d"
    resp = requests.get(url, timeout=12)
    resp.raise_for_status()

    raw_text = resp.text.strip()
    if not raw_text or raw_text.lower().startswith('no data'):
        raise RuntimeError("stooq: no data returned")

    from io import StringIO
    df = pd.read_csv(StringIO(raw_text))
    required_columns = {"Date", "Open", "High", "Low", "Close", "Volume"}
    if not required_columns.issubset(set(df.columns)):
        raise RuntimeError("stooq: invalid csv schema")

    out = pd.DataFrame({
        "date": pd.to_datetime(df["Date"], errors='coerce'),
        "open": pd.to_numeric(df["Open"], errors='coerce'),
        "high": pd.to_numeric(df["High"], errors='coerce'),
        "low": pd.to_numeric(df["Low"], errors='coerce'),
        "close": pd.to_numeric(df["Close"], errors='coerce'),
        "volume": pd.to_numeric(df["Volume"], errors='coerce').fillna(0.0),
    }).dropna(subset=["date", "open", "high", "low", "close"])

    if out.empty:
        raise RuntimeError("stooq: no valid rows after normalization")

    sd = _parse_date_input(start_date)
    ed = _parse_date_input(end_date)
    if sd is not None:
        out = out[out['date'] >= sd]
    if ed is not None:
        out = out[out['date'] <= ed]

    out = out.sort_values('date').reset_index(drop=True)
    if out.empty:
        raise RuntimeError("stooq: no data in requested range")
    return out

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
        except OSError:
            # 在某些文件系统上 os.replace 可能失败，回退到写入直接覆盖
            try:
                df.to_csv(cache_file, index=False)
            except OSError:
                pass  # 保存缓存失败不影响主流程
    except Exception:
        pass  # 保存缓存失败不影响主流程


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
    if source_name == 'tencent':
        return timestamp.strftime('%Y-%m-%d')
    if source_name in ('sina', 'cailianpress'):
        return timestamp.strftime('%Y-%m-%d')
    return timestamp.strftime('%Y%m%d')


def _format_symbol_for_tencent(symbol: str) -> str:
    """将代码转为腾讯接口需要的市场前缀格式。"""
    s = str(symbol).strip().lower()
    if s.startswith('sh') or s.startswith('sz'):
        return s
    if s.isdigit() and len(s) == 6:
        return f"sh{s}" if s.startswith('6') else f"sz{s}"
    return s


def _fetch_from_tencent(symbol: str, start_date: str | None, end_date: str | None) -> pd.DataFrame:
    """从腾讯接口拉取前复权日线并标准化。"""
    symbol_t = _format_symbol_for_tencent(symbol)
    sd = _format_date_for_source(_parse_date_input(start_date), 'tencent') if start_date else '1970-01-01'
    ed = _format_date_for_source(_parse_date_input(end_date), 'tencent') if end_date else '2050-01-01'
    url = (
        "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
        f"?param={symbol_t},day,{sd},{ed},640,qfq"
    )
    resp = requests.get(url, timeout=12)
    resp.raise_for_status()
    payload = resp.json()

    data = payload.get('data', {})
    symbol_payload = data.get(symbol_t)
    if not symbol_payload:
        raise RuntimeError('tencent: empty symbol payload')

    rows = symbol_payload.get('qfqday') or symbol_payload.get('day') or []
    if not rows:
        raise RuntimeError('tencent: no data returned')

    out = pd.DataFrame({
        'date': pd.to_datetime([r[0] for r in rows], errors='coerce'),
        'open': pd.to_numeric([r[1] for r in rows], errors='coerce'),
        'close': pd.to_numeric([r[2] for r in rows], errors='coerce'),
        'high': pd.to_numeric([r[3] for r in rows], errors='coerce'),
        'low': pd.to_numeric([r[4] for r in rows], errors='coerce'),
        'volume': pd.Series(pd.to_numeric([r[5] for r in rows], errors='coerce')).fillna(0.0),
    }).dropna(subset=['date', 'open', 'high', 'low', 'close'])

    if out.empty:
        raise RuntimeError('tencent: no valid rows after normalization')

    return out.sort_values('date').reset_index(drop=True)


def _parse_jsonp(text: str):
    """解析 JSONP 文本并返回 JSON 部分。"""
    s = (text or '').strip()
    if not s:
        return None
    if s[0] in ('{', '['):
        return requests.models.complexjson.loads(s)
    left = s.find('(')
    right = s.rfind(')')
    if left >= 0 and right > left:
        inner = s[left + 1:right]
        return requests.models.complexjson.loads(inner)
    return requests.models.complexjson.loads(s)


def _filter_by_optional_range(df: pd.DataFrame, start_date: str | None, end_date: str | None) -> pd.DataFrame:
    out = df
    sd = _parse_date_input(start_date)
    ed = _parse_date_input(end_date)
    if sd is not None:
        out = out[out['date'] >= sd]
    if ed is not None:
        out = out[out['date'] <= ed]
    return out.sort_values('date').reset_index(drop=True)


def _fetch_from_sina(symbol: str, start_date: str | None, end_date: str | None) -> pd.DataFrame:
    """使用新浪 K 线接口拉取日线数据（240分钟K线近似日线）。"""
    symbol_t = _format_symbol_for_tencent(symbol)
    url = (
        "https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20_sina_kline=/"
        f"CN_MarketDataService.getKLineData?symbol={symbol_t}&scale=240&ma=no&datalen=2048"
    )
    resp = requests.get(url, timeout=12)
    resp.raise_for_status()
    rows = _parse_jsonp(resp.text) or []
    if not isinstance(rows, list) or not rows:
        raise RuntimeError('sina: no data returned')

    out = pd.DataFrame({
        'date': pd.to_datetime([r.get('day') for r in rows], errors='coerce'),
        'open': pd.to_numeric([r.get('open') for r in rows], errors='coerce'),
        'high': pd.to_numeric([r.get('high') for r in rows], errors='coerce'),
        'low': pd.to_numeric([r.get('low') for r in rows], errors='coerce'),
        'close': pd.to_numeric([r.get('close') for r in rows], errors='coerce'),
        'volume': pd.Series(pd.to_numeric([r.get('volume') for r in rows], errors='coerce')).fillna(0.0),
    }).dropna(subset=['date', 'open', 'high', 'low', 'close'])

    out = _filter_by_optional_range(out, start_date, end_date)
    if out.empty:
        raise RuntimeError('sina: no data in requested range')
    return out


def _fetch_from_sohu(symbol: str, start_date: str | None, end_date: str | None) -> pd.DataFrame:
    """使用搜狐历史行情接口拉取日线数据。"""
    code = str(symbol).strip()
    sd = _format_date_for_source(_parse_date_input(start_date), 'akshare') if start_date else '19700101'
    ed = _format_date_for_source(_parse_date_input(end_date), 'akshare') if end_date else '20500101'
    url = (
        "https://q.stock.sohu.com/hisHq"
        f"?code=cn_{code}&start={sd}&end={ed}&stat=1&order=D&period=d&rt=jsonp"
    )
    resp = requests.get(url, timeout=12)
    resp.raise_for_status()
    payload = _parse_jsonp(resp.text)
    if not isinstance(payload, list) or not payload:
        raise RuntimeError('sohu: no data returned')

    hq_rows = payload[0].get('hq') or []
    if not hq_rows:
        raise RuntimeError('sohu: empty hq rows')

    normalized = []
    for row in hq_rows:
        if not isinstance(row, list) or len(row) < 8:
            continue
        # 搜狐字段：日期, 开盘, 收盘, 涨跌额, 涨跌幅, 最低, 最高, 成交量(手), ...
        normalized.append({
            'date': row[0],
            'open': row[1],
            'close': row[2],
            'low': row[5],
            'high': row[6],
            'volume': row[7],
        })

    out = pd.DataFrame(normalized)
    if out.empty:
        raise RuntimeError('sohu: no valid row structure')

    out['date'] = pd.to_datetime(out['date'], errors='coerce')
    out['open'] = pd.to_numeric(out['open'], errors='coerce')
    out['high'] = pd.to_numeric(out['high'], errors='coerce')
    out['low'] = pd.to_numeric(out['low'], errors='coerce')
    out['close'] = pd.to_numeric(out['close'], errors='coerce')
    out['volume'] = pd.Series(pd.to_numeric(out['volume'], errors='coerce')).fillna(0.0)
    out = out.dropna(subset=['date', 'open', 'high', 'low', 'close'])

    out = _filter_by_optional_range(out, start_date, end_date)
    if out.empty:
        raise RuntimeError('sohu: no data in requested range')
    return out


def _fetch_from_eastmoney(symbol: str, start_date: str | None, end_date: str | None) -> pd.DataFrame:
    """使用东方财富官方 K 线接口拉取日线数据。"""
    s = str(symbol).strip()
    secid = f"1.{s}" if s.startswith('6') else f"0.{s}"
    beg = _format_date_for_source(_parse_date_input(start_date), 'akshare') if start_date else '19700101'
    end = _format_date_for_source(_parse_date_input(end_date), 'akshare') if end_date else '20500101'
    url = (
        "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        f"?secid={secid}&klt=101&fqt=1&beg={beg}&end={end}"
        "&fields1=f1,f2,f3&fields2=f51,f52,f53,f54,f55,f56"
    )
    resp = requests.get(url, timeout=12)
    resp.raise_for_status()
    payload = resp.json()
    data = payload.get('data') or {}
    klines = data.get('klines') or []
    if not klines:
        raise RuntimeError('eastmoney: no data returned')

    rows = []
    for line in klines:
        parts = str(line).split(',')
        if len(parts) < 6:
            continue
        rows.append({
            'date': parts[0],
            'open': parts[1],
            'close': parts[2],
            'high': parts[3],
            'low': parts[4],
            'volume': parts[5],
        })
    out = pd.DataFrame(rows)
    if out.empty:
        raise RuntimeError('eastmoney: invalid kline payload')

    out['date'] = pd.to_datetime(out['date'], errors='coerce')
    out['open'] = pd.to_numeric(out['open'], errors='coerce')
    out['high'] = pd.to_numeric(out['high'], errors='coerce')
    out['low'] = pd.to_numeric(out['low'], errors='coerce')
    out['close'] = pd.to_numeric(out['close'], errors='coerce')
    out['volume'] = pd.Series(pd.to_numeric(out['volume'], errors='coerce')).fillna(0.0)
    out = out.dropna(subset=['date', 'open', 'high', 'low', 'close'])

    out = _filter_by_optional_range(out, start_date, end_date)
    if out.empty:
        raise RuntimeError('eastmoney: no data in requested range')
    return out


def _fetch_from_cailianpress(symbol: str, start_date: str | None, end_date: str | None) -> pd.DataFrame:
    """使用财联社行情接口拉取日线数据（可用性受服务端策略影响）。"""
    symbol_t = _format_symbol_for_tencent(symbol)
    url = (
        "https://x-quote.cls.cn/quote/stock/kline"
        f"?secu_code={symbol_t}&type=fd1&offset=0&limit=2048"
    )
    resp = requests.get(url, timeout=12)
    resp.raise_for_status()
    payload = resp.json()
    data = payload.get('data') or {}
    rows = data.get('line') or data.get('klines') or []
    if not rows:
        raise RuntimeError('cailianpress: no data returned')

    parsed = []
    for item in rows:
        if isinstance(item, dict):
            dt_raw = item.get('date') or item.get('secu_time') or item.get('time')
            parsed.append({
                'date': dt_raw,
                'open': item.get('open'),
                'high': item.get('high'),
                'low': item.get('low'),
                'close': item.get('close'),
                'volume': item.get('volume') or item.get('vol') or 0,
            })
        elif isinstance(item, (list, tuple)) and len(item) >= 6:
            parsed.append({
                'date': item[0],
                'open': item[1],
                'close': item[2],
                'high': item[3],
                'low': item[4],
                'volume': item[5],
            })

    out = pd.DataFrame(parsed)
    if out.empty:
        raise RuntimeError('cailianpress: unsupported payload structure')

    # 兼容时间戳和日期字符串
    if pd.api.types.is_numeric_dtype(out['date']):
        max_ts = pd.to_numeric(out['date'], errors='coerce').max()
        unit = 'ms' if pd.notna(max_ts) and max_ts > 10_000_000_000 else 's'
        out['date'] = pd.to_datetime(out['date'], errors='coerce', unit=unit)
    else:
        out['date'] = pd.to_datetime(out['date'], errors='coerce')

    out['open'] = pd.to_numeric(out['open'], errors='coerce')
    out['high'] = pd.to_numeric(out['high'], errors='coerce')
    out['low'] = pd.to_numeric(out['low'], errors='coerce')
    out['close'] = pd.to_numeric(out['close'], errors='coerce')
    out['volume'] = pd.Series(pd.to_numeric(out['volume'], errors='coerce')).fillna(0.0)
    out = out.dropna(subset=['date', 'open', 'high', 'low', 'close'])

    out = _filter_by_optional_range(out, start_date, end_date)
    if out.empty:
        raise RuntimeError('cailianpress: no data in requested range')
    return out


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
            sources = ["akshare", "baostock", "tencent", "sina", "sohu", "eastmoney", "cailianpress", "stooq"]
        else:
            sources = [s]
    else:
        raise ValueError("source must be a string or list/tuple of strings")

    errors = []
    # 使用多态 provider 实现
    provider_map = {
        "akshare": lambda: AkshareProvider(max_attempts=max_attempts),
        "baostock": lambda: BaostockProvider(),
        "tencent": lambda: None,
        "sina": lambda: None,
        "sohu": lambda: None,
        "eastmoney": lambda: None,
        "cailianpress": lambda: None,
        "stooq": lambda: None,
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

            if src == 'stooq':
                df = _fetch_from_stooq(symbol=symbol, start_date=fetch_start, end_date=fetch_end)
            elif src == 'tencent':
                df = _fetch_from_tencent(symbol=symbol, start_date=fetch_start, end_date=fetch_end)
            elif src == 'sina':
                df = _fetch_from_sina(symbol=symbol, start_date=fetch_start, end_date=fetch_end)
            elif src == 'sohu':
                df = _fetch_from_sohu(symbol=symbol, start_date=fetch_start, end_date=fetch_end)
            elif src == 'eastmoney':
                df = _fetch_from_eastmoney(symbol=symbol, start_date=fetch_start, end_date=fetch_end)
            elif src == 'cailianpress':
                df = _fetch_from_cailianpress(symbol=symbol, start_date=fetch_start, end_date=fetch_end)
            else:
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
