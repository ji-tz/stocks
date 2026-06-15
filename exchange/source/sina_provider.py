import pandas as pd
import requests

from .base_provider import BaseProvider
from .provider_utils import format_symbol_for_tencent, parse_jsonp, filter_by_optional_range


class SinaProvider(BaseProvider):

    def fetch(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        symbol_t = format_symbol_for_tencent(symbol)
        url = (
            "https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20_sina_kline=/"
            f"CN_MarketDataService.getKLineData?symbol={symbol_t}&scale=240&ma=no&datalen=2048"
        )
        resp = requests.get(url, timeout=12)
        resp.raise_for_status()
        rows = parse_jsonp(resp.text) or []
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

        out = filter_by_optional_range(out, start_date, end_date)
        if out.empty:
            raise RuntimeError('sina: no data in requested range')
        return out
