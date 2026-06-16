import re
import pandas as pd
import requests


def parse_date_input(value: str | None):
    if value is None:
        return None
    value = str(value).strip()
    if value == "":
        return None
    if re.fullmatch(r"\d{8}", value):
        return pd.to_datetime(value, format="%Y%m%d")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return pd.to_datetime(value, format="%Y-%m-%d")
    return pd.to_datetime(value)


def format_date_for_source(value, source_name: str) -> str | None:
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


def format_symbol_for_tencent(symbol: str) -> str:
    s = str(symbol).strip().lower()
    if s.startswith('sh') or s.startswith('sz') or s.startswith('bj'):
        return s
    if s.isdigit() and len(s) == 6:
        if s.startswith('6'):
            return f"sh{s}"
        elif s.startswith('8'):
            return f"bj{s}"
        else:
            return f"sz{s}"
    return s


def format_symbol_for_stooq(symbol: str) -> str:
    normalized = str(symbol).strip().lower()
    if '.' in normalized:
        return normalized
    if normalized.isdigit() and len(normalized) == 6:
        return f"{normalized}.cn"
    return normalized


def parse_jsonp(text: str):
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


def filter_by_optional_range(df: pd.DataFrame, start_date: str | None, end_date: str | None) -> pd.DataFrame:
    out = df
    sd = parse_date_input(start_date)
    ed = parse_date_input(end_date)
    if sd is not None:
        out = out[out['date'] >= sd]
    if ed is not None:
        out = out[out['date'] <= ed]
    return out.sort_values('date').reset_index(drop=True)
