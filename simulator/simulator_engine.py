"""模拟交易引擎实现

实现基于内存的模拟交易功能，用于策略回测。
"""
from datetime import datetime
from typing import Optional

from simulator.base_engine import BaseEngine, TradeResult, TradeOrder


class SimulatorEngine(BaseEngine):
    """模拟交易引擎

    基于内存的模拟交易实现，用于策略回测。
    特点：
    - 不需要连接真实交易系统
    - 可以快速执行大量历史数据回测
    - 支持完整的买卖操作和账户管理
    """

    def __init__(self, init_cash: float = 100000.0, lot_size: float = 100.0, verbose: bool = False):
        """初始化模拟引擎

        Args:
            init_cash: 初始资金
            lot_size: 交易手数
            verbose: 是否打印详细信息
        """
        super().__init__(init_cash=init_cash, lot_size=lot_size)
        self.verbose = verbose
        self.trade_count = 0  # 交易次数

    def buy(self, date: datetime, price: float, shares: Optional[float] = None) -> TradeResult:
        """买入股票

        检查资金是否充足，如果充足则执行买入操作。

        Args:
            date: 交易日期
            price: 买入价格
            shares: 买入股数（可选）。如果不指定，使用默认的 lot_size

        Returns:
            TradeResult: 交易结果，包含是否成功及详细信息
        """
        # 如果没有指定股数，使用默认的 lot_size
        buy_shares = float(shares) if shares is not None else self.lot_size
        
        # 股数必须是正数
        if buy_shares <= 0:
            if self.verbose:
                print(f"[{date.strftime('%Y-%m-%d')}] 买入失败：股数必须为正数 ({buy_shares})")
            return TradeResult(
                success=False,
                message=f"股数必须为正数：{buy_shares}",
                cash_after=self.account.cash,
                shares_after=self.account.position.shares
            )
        
        cost = price * buy_shares

        # 检查资金是否充足
        if self.account.cash < cost:
            if self.verbose:
                print(f"[{date.strftime('%Y-%m-%d')}] 买入失败：资金不足 (需要 {cost:.2f}, 可用 {self.account.cash:.2f})")
            return TradeResult(
                success=False,
                message=f"资金不足：需要 {cost:.2f}，可用 {self.account.cash:.2f}",
                cash_after=self.account.cash,
                shares_after=self.account.position.shares
            )

        # 执行买入
        self.account.cash -= cost
        self.account.position.shares += buy_shares
        self.account.position.total_cost += cost
        self.account.position.avg_cost = (
            self.account.position.total_cost / self.account.position.shares
            if self.account.position.shares > 0 else 0.0
        )
        self.trade_count += 1

        order = TradeOrder(date=date, action='buy', price=price, shares=buy_shares)

        if self.verbose:
            print(f"[{date.strftime('%Y-%m-%d')}] 买入成功：价格 {price:.2f}, 数量 {buy_shares}, "
                  f"成本 {cost:.2f}, 剩余现金 {self.account.cash:.2f}")

        return TradeResult(
            success=True,
            message="买入成功",
            order=order,
            cash_after=self.account.cash,
            shares_after=self.account.position.shares
        )

    def sell(self, date: datetime, price: float) -> TradeResult:
        """卖出股票

        检查持仓是否充足，如果充足则执行卖出操作。

        Args:
            date: 交易日期
            price: 卖出价格

        Returns:
            TradeResult: 交易结果，包含是否成功及详细信息
        """
        # 检查持仓是否充足
        if self.account.position.shares < self.lot_size:
            if self.verbose:
                print(f"[{date.strftime('%Y-%m-%d')}] 卖出失败：持仓不足 "
                      f"(需要 {self.lot_size}, 持有 {self.account.position.shares})")
            return TradeResult(
                success=False,
                message=f"持仓不足：需要 {self.lot_size}，持有 {self.account.position.shares}",
                cash_after=self.account.cash,
                shares_after=self.account.position.shares
            )

        # 计算收益
        proceeds = price * self.lot_size
        avg_cost = self.account.position.avg_cost
        cost_reduced = avg_cost * self.lot_size
        realized_pl_this = (price - avg_cost) * self.lot_size

        # 执行卖出
        self.account.cash += proceeds
        self.account.position.shares -= self.lot_size
        self.account.position.total_cost -= cost_reduced
        self.realized_pl += realized_pl_this
        self.trade_count += 1

        # 更新平均成本
        if self.account.position.shares > 0:
            self.account.position.avg_cost = (
                self.account.position.total_cost / self.account.position.shares
            )
        else:
            self.account.position.avg_cost = 0.0
            self.account.position.total_cost = 0.0

        order = TradeOrder(date=date, action='sell', price=price, shares=self.lot_size)

        if self.verbose:
            print(f"[{date.strftime('%Y-%m-%d')}] 卖出成功：价格 {price:.2f}, 数量 {self.lot_size}, "
                  f"收入 {proceeds:.2f}, 本次盈亏 {realized_pl_this:.2f}, "
                  f"累计盈亏 {self.realized_pl:.2f}, 现金 {self.account.cash:.2f}")

        return TradeResult(
            success=True,
            message="卖出成功",
            order=order,
            cash_after=self.account.cash,
            shares_after=self.account.position.shares,
            realized_pl=realized_pl_this
        )

    def print_daily_status(self, date: datetime, price_open: float, price_close: float,
                          action: Optional[str] = None) -> None:
        """打印每日状态

        Args:
            date: 日期
            price_open: 开盘价
            price_close: 收盘价
            action: 执行的操作（buy/sell/None）
        """
        if not self.verbose:
            return

        pos = self.account.position
        market_value = pos.shares * price_close
        total_value = self.account.cash + market_value
        unrealized_pl = ((price_close - pos.avg_cost) * pos.shares) if pos.shares > 0 else 0.0

        action_str = f"操作: {action}" if action else "操作: 持有"

        print(f"[{date.strftime('%Y-%m-%d')}] "
              f"开盘: {price_open:.2f} | 收盘: {price_close:.2f} | "
              f"{action_str} | "
              f"持仓: {pos.shares} | "
              f"成本: {pos.avg_cost:.2f} | "
              f"现金: {self.account.cash:.2f} | "
              f"市值: {market_value:.2f} | "
              f"总值: {total_value:.2f} | "
              f"浮盈: {unrealized_pl:.2f}")
