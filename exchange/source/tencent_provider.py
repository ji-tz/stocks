import pandas as pd
import requests

from .base_provider import BaseProvider
from .provider_utils import format_symbol_for_tencent, format_date_for_source, parse_date_input


class TencentProvider(BaseProvider):

    def fetch(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        symbol_t = format_symbol_for_tencent(symbol)
        sd = format_date_for_source(parse_date_input(start_date), 'tencent') if start_date else '1970-01-01'
        ed = format_date_for_source(parse_date_input(end_date), 'tencent') if end_date else '2050-01-01'
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
