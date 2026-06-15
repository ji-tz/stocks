from typing import Any

import pandas as pd


AUTO_STRATEGY_SPEC = {
    "key": "sma",
    "label": "SMA",
    "runner": "run_module_strategy_backtest",
    "module_interface": True,
    "parameters": [
        {
            "name": "period",
            "label": "SMA 周期",
            "caster": "int",
            "default": 20,
            "description": "移动平均线周期",
        },
    ],
    "description": "基于移动平均线的趋势策略",
    "supported_trade_prices": ["open"],
}


def validate_strategy_parameters(period: int = 20, **kwargs) -> None:
    """校验 SMA 策略参数。"""
    if period <= 0:
        raise ValueError('SMA 周期必须大于 0')


def prepare_backtest_data(df: pd.DataFrame, period: int = 20, **kwargs) -> pd.DataFrame:
    """为 SMA 策略补充均线指标列。"""
    prepared = df.copy()
    prepared["sma"] = prepared["close"].rolling(window=period, min_periods=1).mean()
    return prepared


def create_strategy(df: pd.DataFrame, period: int = 20, **kwargs) -> 'SmaDecision':
    """构造 SMA 策略决策器。"""
    return SmaDecision(period=period, df=df)


class SmaDecision:
    """决策器：用于 pandas 模拟的 SMA 决策逻辑。

    - 当没有持仓且当日收盘价 > SMA(period) 时返回 'buy'
    - 当持仓且当日收盘价 < SMA(period) 时返回 'sell'
    - 否则返回 None
    """

    def __init__(self, period: int = 20, df=None):
        self.period = period
        self.df = df

    def simulate(self, open_price: float, close_price: float, avg_cost: float = 0.0, shares: float = 0.0,
                 date: Any = None, trade_price: float | None = None, trade_price_field: str = 'open') -> str | None:
        """根据 SMA 信号决定买卖操作。

        Args:
            open_price: 当日开盘价（此策略未使用）
            close_price: 当日收盘价，与 SMA 比较的价格
            avg_cost: 持仓平均成本（此策略未使用）
            shares: 当前持仓数量
            date: 当前交易日期，用于查询预计算的 SMA 值
            trade_price: 可选的成交价格覆盖（此策略未使用）
            trade_price_field: 成交价格字段名称（此策略未使用）

        Returns:
            'buy' 表示买入，'sell' 表示卖出，None 表示不操作
        """
        if self.df is None or date is None:
            return None
        try:
            row = self.df[self.df['date'] == date]
            if row.empty:
                return None
            sma = float(row['sma'].iloc[0])
        except Exception:
            return None

        if shares <= 0 and close_price > sma:
            return 'buy'
        if shares > 0 and close_price < sma:
            return 'sell'
        return None

    def decide(self, open_price: float, close_price: float, avg_cost: float = 0.0, shares: float = 0.0,
               date: Any = None, trade_price: float | None = None, trade_price_field: str = 'open') -> str | None:
        """根据 SMA 信号决定买卖操作（已弃用，请使用 simulate()）。"""
        return self.simulate(
            open_price=open_price, close_price=close_price, avg_cost=avg_cost, shares=shares,
            date=date, trade_price=trade_price, trade_price_field=trade_price_field)
