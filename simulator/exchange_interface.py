"""股票交易所统一接口定义。"""

from abc import abstractmethod
from datetime import datetime
from typing import Optional

from simulator.base_engine import BaseEngine, TradeResult


class StockExchange(BaseEngine):
    """股票交易所统一接口。

    三类实现（回测仿真、实时仿真、实盘交易）都必须遵循本接口。
    """

    @abstractmethod
    def connect(self) -> bool:
        """连接交易系统或初始化交易会话。"""

    @abstractmethod
    def disconnect(self) -> None:
        """断开交易系统连接。"""

    @abstractmethod
    def buy(self, date: datetime, price: float, shares: Optional[float] = None) -> TradeResult:
        """买入。"""

    @abstractmethod
    def sell(self, date: datetime, price: float, shares: Optional[float] = None) -> TradeResult:
        """卖出。"""

    @abstractmethod
    def get_real_time_price(self, symbol: str) -> float:
        """获取实时行情价格。"""

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """撤单。"""
