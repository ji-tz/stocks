import dataclasses
from typing import Any, Optional

import pandas as pd


AUTO_STRATEGY_SPEC = {
    "key": "rsi",
    "label": "RSI",
    "runner": "run_module_strategy_backtest",
    "module_interface": True,
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
    df: Optional[pd.DataFrame] = None

    def simulate(
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

        if shares <= 0 and rsi_value < self.oversold:
            return "buy"
        if shares > 0 and rsi_value > self.overbought:
            return "sell"
        return None

    def decide(
        self,
        open_price: float,
        close_price: float | None = None,
        avg_cost: float = 0.0,
        shares: float = 0.0,
        date: Any = None,
    ) -> str | None:
        """已弃用，请使用 simulate()。"""
        return self.simulate(open_price=open_price, close_price=close_price, avg_cost=avg_cost, shares=shares, date=date)


def validate_strategy_parameters(period: int = 14, oversold: float = 30.0, overbought: float = 70.0, **kwargs) -> None:
    """校验 RSI 策略参数。"""
    if period <= 0:
        raise ValueError('RSI 周期必须大于 0')
    if not 0 <= oversold < overbought <= 100:
        raise ValueError('RSI 阈值必须满足 0 <= oversold < overbought <= 100')


def prepare_backtest_data(df: pd.DataFrame, period: int = 14, **kwargs) -> pd.DataFrame:
    """为 RSI 策略补充 RSI 指标列。"""
    prepared = df.copy()
    delta = prepared["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.where(avg_loss != 0)
    prepared["rsi"] = 100 - (100 / (1 + rs))
    prepared.loc[(avg_loss == 0) & (avg_gain > 0), "rsi"] = 100.0
    prepared.loc[(avg_loss == 0) & (avg_gain == 0), "rsi"] = 50.0
    return prepared


def create_strategy(df: pd.DataFrame, period: int = 14,
                    oversold: float = 30.0, overbought: float = 70.0, **kwargs) -> RsiDecision:
    """构造 RSI 策略决策器。"""
    return RsiDecision(period=period, oversold=oversold, overbought=overbought, df=df)
