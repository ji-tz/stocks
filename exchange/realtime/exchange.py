"""实时仿真交易所实现。"""
from datetime import datetime
from typing import Optional

from exchange.simulated_exchange import SimulatedExchangeBase
from exchange.base_engine import TradeResult, TradeOrder


class RealtimeSimExchange(SimulatedExchangeBase):
    """实时仿真交易所：接口与回测、实盘一致，便于无缝切换。

    用于模拟盘（paper trading），在 SimulatedExchangeBase 的基础上
    增加 stock_code 参数和交易历史记录。
    """

    def __init__(self, stock_code: str = '',
                 init_cash: float = 100000.0,
                 lot_size: float = 100.0,
                 verbose: bool = False,
                 commission_pct: float = 0.00025,
                 stamp_duty_pct: float = 0.001,
                 slippage_pct: float = 0.0):
        super().__init__(init_cash=init_cash, lot_size=lot_size, verbose=verbose,
                         commission_pct=commission_pct, stamp_duty_pct=stamp_duty_pct,
                         slippage_pct=slippage_pct)
        self.stock_code = stock_code
        self.trade_history: list[dict] = []

    def buy(self, date: datetime, price: float,
            shares: Optional[float] = None) -> TradeResult:
        result = super().buy(date, price, shares)
        if result.success:
            actual_shares = shares if shares is not None else self.lot_size
            self.trade_history.append({
                'date': date.strftime('%Y-%m-%d %H:%M:%S') if hasattr(date, 'strftime') else str(date),
                'action': 'buy',
                'price': price,
                'shares': actual_shares,
            })
        return result

    def sell(self, date: datetime, price: float,
             shares: Optional[float] = None) -> TradeResult:
        result = super().sell(date, price, shares)
        if result.success:
            actual_shares = shares if shares is not None else self.lot_size
            self.trade_history.append({
                'date': date.strftime('%Y-%m-%d %H:%M:%S') if hasattr(date, 'strftime') else str(date),
                'action': 'sell',
                'price': price,
                'shares': actual_shares,
            })
        return result
