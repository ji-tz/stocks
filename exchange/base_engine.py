"""交易引擎抽象基类

定义统一的交易引擎接口，支持模拟交易（simulator）和实盘交易（real）。
这个抽象层使得不同的交易引擎可以互换使用，便于测试和实际部署。
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Position:
    """持仓信息"""
    shares: float = 0.0  # 持股数量（支持基金按份额小数交易）
    avg_cost: float = 0.0  # 平均成本
    total_cost: float = 0.0  # 总成本


@dataclass
class Account:
    """账户信息"""
    cash: float = 100000.0  # 现金
    position: Optional[Position] = None  # 持仓

    def __post_init__(self):
        if self.position is None:
            self.position = Position()

    def get_total_value(self, current_price: float) -> float:
        """获取总资产价值"""
        market_value = self.position.shares * current_price
        return self.cash + market_value


@dataclass
class TradeOrder:
    """交易订单"""
    date: datetime  # 交易日期
    action: str  # 'buy' 或 'sell'
    price: float  # 交易价格
    shares: float  # 交易股数


@dataclass
class TradeResult:
    """交易执行结果"""
    success: bool  # 是否成功
    message: str = ""  # 消息说明
    order: Optional[TradeOrder] = None  # 订单信息
    cash_after: float = 0.0  # 交易后现金
    shares_after: float = 0.0  # 交易后持股
    realized_pl: float = 0.0  # 已实现盈亏


class BaseEngine(ABC):
    """交易引擎抽象基类

    定义交易引擎的统一接口，支持：
    - 买入/卖出操作
    - 查询账户状态
    - 查询持仓信息

    子类实现：
    - SimulatorEngine: 模拟交易引擎（回测）
    - RealEngine: 实盘交易引擎（实际交易，预留）
    """

    def __init__(self, init_cash: float = 100000.0, lot_size: float = 100.0,
                 commission_pct: float = 0.00025, stamp_duty_pct: float = 0.001,
                 slippage_pct: float = 0.0):
        """初始化交易引擎

        Args:
            init_cash: 初始资金
            lot_size: 交易手数（每次买卖的股数）
            commission_pct: 佣金比例（如 0.00025 表示万分之二点五）
            stamp_duty_pct: 印花税比例（卖出时收取，如 0.001 表示千分之一）
            slippage_pct: 滑点比例（如 0.001 表示千分之一）
        """
        self.lot_size = float(lot_size)
        self.account = Account(cash=init_cash)
        self.realized_pl = 0.0  # 累计已实现盈亏
        self.total_fees = 0.0  # 累计交易费用（佣金 + 印花税）
        self.commission_pct = commission_pct
        self.stamp_duty_pct = stamp_duty_pct
        self.slippage_pct = slippage_pct

    @abstractmethod
    def buy(self, date: datetime, price: float) -> TradeResult:
        """买入股票

        Args:
            date: 交易日期
            price: 买入价格

        Returns:
            TradeResult: 交易结果
        """
        pass

    @abstractmethod
    def sell(self, date: datetime, price: float) -> TradeResult:
        """卖出股票

        Args:
            date: 交易日期
            price: 卖出价格

        Returns:
            TradeResult: 交易结果
        """
        pass

    def get_cash(self) -> float:
        """获取当前现金"""
        return self.account.cash

    def get_position(self) -> Position:
        """获取当前持仓"""
        return self.account.position

    def get_account(self) -> Account:
        """获取账户信息"""
        return self.account

    def get_total_value(self, current_price: float) -> float:
        """获取总资产价值"""
        return self.account.get_total_value(current_price)

    def get_summary(self, current_price: float) -> Dict[str, Any]:
        """获取账户摘要

        Args:
            current_price: 当前股价

        Returns:
            包含账户详细信息的字典
        """
        pos = self.account.position
        market_value = pos.shares * current_price
        unrealized_pl = ((current_price - pos.avg_cost) * pos.shares) if pos.shares > 0 else 0.0
        total_value = self.account.cash + market_value

        return {
            'cash': round(self.account.cash, 2),
            'shares': pos.shares,
            'avg_cost': round(pos.avg_cost, 4),
            'market_value': round(market_value, 2),
            'total_value': round(total_value, 2),
            'realized_pl': round(self.realized_pl, 4),
            'unrealized_pl': round(unrealized_pl, 4),
            'total_fees': round(self.total_fees, 4),
        }
