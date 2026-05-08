import dataclasses
from typing import Any

import pandas as pd


AUTO_STRATEGY_SPEC = {
    "key": "rsi",
    "label": "RSI",
    "runner": "run_rsi_backtest",
    "parameters": [
        {
            "name": "period",
            "label": "RSI 周期",
            "caster": "int",
            "default": 14,
            "description": "RSI 指标窗口，默认 14 日",
        },
        {
            "name": "oversold",
            "label": "超卖阈值",
            "caster": "float",
            "default": 30.0,
            "description": "RSI 低于该值时尝试买入",
        },
        {
            "name": "overbought",
            "label": "超买阈值",
            "caster": "float",
            "default": 70.0,
            "description": "RSI 高于该值时尝试卖出",
        },
    ],
    "description": "RSI 超卖买入、超买卖出",
    "supported_trade_prices": ["open"],
}


@dataclasses.dataclass
class RsiDecision:
    """RSI 超买超卖策略。"""

    period: int = 14
    oversold: float = 30.0
    overbought: float = 70.0
    df: pd.DataFrame | None = None

    def decide(
        self,
        open_price: float,
        close_price: float | None = None,
        avg_cost: float = 0.0,
        shares: float = 0.0,
        date: Any = None,
    ) -> str | None:
        _ = open_price, close_price, avg_cost
        if self.df is None or date is None:
            return None

        rows = self.df[self.df["date"] == date]
        if rows.empty:
            return None

        rsi_value = rows.iloc[-1]["rsi"]
        if pd.isna(rsi_value):
            return None

        rsi_value = float(rsi_value)
        if shares <= 0 and rsi_value < self.oversold:
            return "buy"
        if shares > 0 and rsi_value > self.overbought:
            return "sell"
        return None
