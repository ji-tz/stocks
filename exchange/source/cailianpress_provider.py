import pandas as pd
import requests

from .base_provider import BaseProvider
from .provider_utils import format_symbol_for_tencent, filter_by_optional_range


class CailianpressProvider(BaseProvider):

    def fetch(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        symbol_t = format_symbol_for_tencent(symbol)
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

        out = filter_by_optional_range(out, start_date, end_date)
        if out.empty:
            raise RuntimeError('cailianpress: no data in requested range')
        return out
