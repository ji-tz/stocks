import dataclasses
import datetime
from typing import Any, Optional

import pandas as pd

from exchange.source.data_provider import get_data


AUTO_STRATEGY_SPEC = {
    "key": "a50_prev_night_1h",
    "label": "A50 前夜信号(1h)",
    "runner": "run_futures_a50_prev_night",
    "parameters": [
        {
            "name": "futures_symbol",
            "label": "A50 期货代码",
            "caster": "str",
            "default": "CN00Y",
            "description": "用于判断前一晚涨跌的期货标的代码，默认 CN00Y（A50期指当月连续）",
        },
        {
            "name": "base_position_lots",
            "label": "底仓手数",
            "caster": "int",
            "default": 2,
            "description": "A股 T+1 日内策略所需底仓，默认2手",
        },
    ],
    "description": "根据前一晚A50涨跌判断是否买入，买入后1小时卖出",
    "supported_trade_prices": ["open"],
}


@dataclasses.dataclass
class FuturesOpenHourDecision:
    """根据前一晚富时A50期货涨跌决定是否买入，并预约1小时后卖出。"""

    futures_symbol: str = "CN00Y"
    source: object = "auto"
    lookback_days: int = 20
    futures_df: Optional[pd.DataFrame] = None
    _bought_dates: set[str] = dataclasses.field(default_factory=set, init=False, repr=False)
    _base_shares: Optional[float] = dataclasses.field(default=None, init=False, repr=False)

    def _ensure_futures_df(self, date: Any) -> Optional[pd.DataFrame]:
        if self.futures_df is not None:
            return self.futures_df

        try:
            end_dt = pd.to_datetime(date)
            start_dt = end_dt - datetime.timedelta(days=max(5, self.lookback_days))
            df = get_data(
                symbol=self.futures_symbol,
                source=self.source,
                start_date=start_dt.strftime("%Y%m%d"),
                end_date=end_dt.strftime("%Y%m%d"),
            )
            if df is None or df.empty:
                return None
            self.futures_df = df.sort_values("date").reset_index(drop=True)
            return self.futures_df
        except Exception:
            return None

    def _is_prev_night_up(self, date: Any) -> Optional[bool]:
        """判断“前一晚”是否上涨：比较前一交易日与前二交易日收盘价。"""
        df = self._ensure_futures_df(date)
        if df is None or df.empty:
            return None

        current_dt = pd.to_datetime(date)
        hist = df[df["date"] < current_dt].sort_values("date").reset_index(drop=True)
        if len(hist) < 2:
            return None

        last_close = float(hist.iloc[-1]["close"])
        prev_close = float(hist.iloc[-2]["close"])
        return last_close > prev_close

    def decide(
        self,
        open_price: float,
        close_price: float | None = None,
        avg_cost: float = 0.0,
        shares: float = 0.0,
        date: Any = None,
        schedule_order=None,
        **kwargs,
    ):
        _ = open_price, close_price, avg_cost, kwargs
        if date is None:
            return None

        if self._base_shares is None:
            # 首次决策时记下底仓基线：允许在“仅持有底仓”时继续做日内 T+0。
            self._base_shares = max(float(shares), 0.0)

        is_up = self._is_prev_night_up(date)
        if is_up is None:
            return None

        if is_up and float(shares) <= float(self._base_shares):
            date_key = pd.to_datetime(date).strftime("%Y-%m-%d")
            if date_key in self._bought_dates:
                return None
            if callable(schedule_order):
                schedule_order(action="sell", after_hours=1, tag="a50_prev_night_exit")
            self._bought_dates.add(date_key)
            return "buy"

        return None
