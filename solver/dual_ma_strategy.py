import dataclasses
from typing import Any, Optional

import pandas as pd


AUTO_STRATEGY_SPEC = {
    "key": "dual_ma",
    "label": "双均线交叉",
    "runner": "run_dual_ma_backtest",
    "parameters": [
        {
            "name": "short_period",
            "label": "短期均线周期",
            "caster": "int",
            "default": 5,
            "description": "短周期移动平均线窗口，默认 5 日",
        },
        {
            "name": "long_period",
            "label": "长期均线周期",
            "caster": "int",
            "default": 20,
            "description": "长周期移动平均线窗口，默认 20 日",
        },
    ],
    "description": "短期均线上穿长期均线买入，下穿时卖出",
    "supported_trade_prices": ["open"],
}


@dataclasses.dataclass
class DualMaDecision:
    """双均线交叉策略。"""

    short_period: int = 5
    long_period: int = 20
    df: Optional[pd.DataFrame] = None

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

        rows = self.df[self.df["date"] <= date].tail(2)
        if len(rows) < 2:
            return None

        prev_row = rows.iloc[-2]
        current_row = rows.iloc[-1]
        if any(
            pd.isna(value)
            for value in (
                prev_row["ma_short"],
                prev_row["ma_long"],
                current_row["ma_short"],
                current_row["ma_long"],
            )
        ):
            return None

        prev_short = float(prev_row["ma_short"])
        prev_long = float(prev_row["ma_long"])
        current_short = float(current_row["ma_short"])
        current_long = float(current_row["ma_long"])

        if shares <= 0 and prev_short <= prev_long and current_short > current_long:
            return "buy"
        if shares > 0 and prev_short >= prev_long and current_short < current_long:
            return "sell"
        return None
