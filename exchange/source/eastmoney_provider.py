import pandas as pd
import requests

from .base_provider import BaseProvider
from .provider_utils import format_date_for_source, parse_date_input, filter_by_optional_range


class EastmoneyProvider(BaseProvider):

    def fetch(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        s = str(symbol).strip()
        secid = self._resolve_secid(s)
        beg = format_date_for_source(parse_date_input(start_date), 'akshare') if start_date else '19700101'
        end = format_date_for_source(parse_date_input(end_date), 'akshare') if end_date else '20500101'
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

        out = filter_by_optional_range(out, start_date, end_date)
        if out.empty:
            raise RuntimeError('eastmoney: no data in requested range')
        return out

    @staticmethod
    def _resolve_secid(symbol: str) -> str:
        """Map a symbol to the Eastmoney secid format based on market.

        Eastmoney secid schemes:
          - Shanghai (6xxxxx)      -> 1.{code}
          - Shenzhen (0xxxxx/3xxxxx) -> 0.{code}
          - Beijing (8xxxxx)      -> 2.{code}
          - Hong Kong (*.HK)      -> h{code_without_dot_HK}

        Returns the secid string or raises RuntimeError for unknown markets
        so the caller can gracefully fall through to the next provider.
        """
        s = str(symbol).strip()

        # Hong Kong: symbol ends with .HK
        if s.upper().endswith('.HK'):
            code = s[:-3]  # strip '.HK'
            return f"h{code}"

        # Beijing: starts with '8'
        if s.startswith('8'):
            return f"2.{s}"

        # Shanghai: starts with '6'
        if s.startswith('6'):
            return f"1.{s}"

        # Shenzhen: starts with '0' or '3' (main board / chiNext)
        if s.startswith(('0', '3')):
            return f"0.{s}"

        # Unknown market — let the caller fall through gracefully
        raise RuntimeError(
            f'eastmoney: unsupported symbol format "{symbol}"'
        )
