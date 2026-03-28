"""实盘交易所实现（预留）。"""

from datetime import datetime
from typing import Optional

from simulator.base_engine import TradeResult
from simulator.exchange_interface import StockExchange


class LiveExchange(StockExchange):
    """实盘交易所：当前仅保留统一接口，尚未接入券商。"""

    def __init__(
        self,
        init_cash: float = 100000.0,
        lot_size: float = 100.0,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
    ):
        super().__init__(init_cash=init_cash, lot_size=lot_size)
        self.api_key = api_key
        self.api_secret = api_secret
        self.connected = False

    def connect(self) -> bool:
        raise NotImplementedError("实盘交易功能尚未实现，请使用回测或实时仿真")

    def disconnect(self) -> None:
        self.connected = False

    def buy(self, date: datetime, price: float, shares: Optional[float] = None) -> TradeResult:
        _ = date, price, shares
        raise NotImplementedError("实盘交易功能尚未实现，请使用回测或实时仿真")

    def sell(self, date: datetime, price: float, shares: Optional[float] = None) -> TradeResult:
        _ = date, price, shares
        raise NotImplementedError("实盘交易功能尚未实现，请使用回测或实时仿真")

    def get_real_time_price(self, symbol: str) -> float:
        _ = symbol
        raise NotImplementedError("实盘交易功能尚未实现")

    def cancel_order(self, order_id: str) -> bool:
        _ = order_id
        raise NotImplementedError("实盘交易功能尚未实现")
