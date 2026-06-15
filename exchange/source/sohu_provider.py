import pandas as pd
import requests

from .base_provider import BaseProvider
from .provider_utils import format_date_for_source, parse_date_input, parse_jsonp, filter_by_optional_range


class SohuProvider(BaseProvider):

    def fetch(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        code = str(symbol).strip()
        sd = format_date_for_source(parse_date_input(start_date), 'akshare') if start_date else '19700101'
        ed = format_date_for_source(parse_date_input(end_date), 'akshare') if end_date else '20500101'
        url = (
            "https://q.stock.sohu.com/hisHq"
            f"?code=cn_{code}&start={sd}&end={ed}&stat=1&order=D&period=d&rt=jsonp"
        )
        resp = requests.get(url, timeout=12)
        resp.raise_for_status()
        payload = parse_jsonp(resp.text)
        if not isinstance(payload, list) or not payload:
            raise RuntimeError('sohu: no data returned')

        hq_rows = payload[0].get('hq') or []
        if not hq_rows:
            raise RuntimeError('sohu: empty hq rows')

        normalized = []
        for row in hq_rows:
            if not isinstance(row, list) or len(row) < 8:
                continue
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

        out = filter_by_optional_range(out, start_date, end_date)
        if out.empty:
            raise RuntimeError('sohu: no data in requested range')
        return out
