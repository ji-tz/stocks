import dataclasses
from typing import Any

import pandas as pd


AUTO_STRATEGY_SPEC = {
    "key": "bollinger",
    "label": "布林带",
    "runner": "run_bollinger_backtest",
    "parameters": [
        {
            "name": "period",
            "label": "布林带周期",
            "caster": "int",
            "default": 20,
            "description": "移动均线与波动率窗口，默认 20 日",
        },
        {
            "name": "std_multiplier",
            "label": "标准差倍数",
            "caster": "float",
            "default": 2.0,
            "description": "上下轨标准差倍数，默认 2.0",
        },
    ],
    "description": "收盘价跌破下轨买入，涨破上轨卖出",
    "supported_trade_prices": ["open"],
}


@dataclasses.dataclass
class BollingerDecision:
    """布林带低频策略。"""

    period: int = 20
    std_multiplier: float = 2.0
    df: pd.DataFrame | None = None

    def decide(
        self,
        open_price: float,
        close_price: float | None = None,
        avg_cost: float = 0.0,
        shares: float = 0.0,
        date: Any = None,
    ) -> str | None:
        _ = open_price, avg_cost
        if self.df is None or date is None or close_price is None:
            return None

        rows = self.df[self.df["date"] == date]
        if rows.empty:
            return None

        row = rows.iloc[-1]
        upper = row["bollinger_upper"]
        lower = row["bollinger_lower"]
        if pd.isna(upper) or pd.isna(lower):
            return None

        if shares <= 0 and float(close_price) < float(lower):
            return "buy"
        if shares > 0 and float(close_price) > float(upper):
            return "sell"
        return None
