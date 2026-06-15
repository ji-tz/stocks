import pandas as pd
import requests
from io import StringIO

from .base_provider import BaseProvider
from .provider_utils import format_symbol_for_stooq, parse_date_input


class StooqProvider(BaseProvider):

    def fetch(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        stooq_symbol = format_symbol_for_stooq(symbol)
        url = f"https://stooq.com/q/d/l/?s={stooq_symbol}&i=d"
        resp = requests.get(url, timeout=12)
        resp.raise_for_status()

        raw_text = resp.text.strip()
        if not raw_text or raw_text.lower().startswith('no data'):
            raise RuntimeError("stooq: no data returned")

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

        sd = parse_date_input(start_date)
        ed = parse_date_input(end_date)
        if sd is not None:
            out = out[out['date'] >= sd]
        if ed is not None:
            out = out[out['date'] <= ed]

        out = out.sort_values('date').reset_index(drop=True)
        if out.empty:
            raise RuntimeError("stooq: no data in requested range")
        return out
