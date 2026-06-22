from typing import Any

import pandas as pd


class SmaDecision:
    """决策器：用于 pandas 模拟的 SMA 决策逻辑。

    - 当没有持仓且当日收盘价 > SMA(period) 时返回 'buy'
    - 当持仓且当日收盘价 < SMA(period) 时返回 'sell'
    - 否则返回 None

    This strategy is tick-safe (works with partial data slices).
    """

    __tick_safe__ = True

    def __init__(self, period: int = 20, df=None):
        self.period = period
        self.df = df

    def decide(self, open_price: float, close_price: float, avg_cost: float = 0.0, shares: float = 0.0,
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
        # close_price 对比 sma 决策由 simulator 预先计算 sma 并放入 df；此处使用 close_price 与 df 中对应 sma 值比较具有上下文耦合。
        # 为了保持简单，假设调用方在构造时给定了 df，并且当前 date 可用于查询 sma。
        if self.df is None or date is None:
            # 退化到仅用 close_price 与 None 比较 -> 无动作
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


def prepare_backtest_data(df: pd.DataFrame, period: int = 20, **kwargs) -> pd.DataFrame:
    """为 SMA 策略补充 SMA 指标列。

    Uses min_periods=1 so early rows get valid SMA values from partial data,
    making this safe for tick-by-tick progression mode.
    """
    prepared = df.copy()
    prepared["sma"] = prepared["close"].rolling(window=period, min_periods=1).mean()
    return prepared
