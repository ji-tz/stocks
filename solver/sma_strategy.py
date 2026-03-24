from typing import Any


class SmaDecision:
    """决策器：用于 pandas 模拟的 SMA 决策逻辑。

    - 当没有持仓且当日收盘价 > SMA(period) 时返回 'buy'
    - 当持仓且当日收盘价 < SMA(period) 时返回 'sell'
    - 否则返回 None
    """

    def __init__(self, period: int = 20, df=None):
        self.period = period
        self.df = df

    def decide(self, open_price: float, close_price: float, avg_cost: float = 0.0, shares: int = 0,
               date: Any = None, trade_price: float | None = None, trade_price_field: str = 'open'):
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

        if shares == 0 and close_price > sma:
            return 'buy'
        if shares >= 1 and close_price < sma:
            return 'sell'
        return None

