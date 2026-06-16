"""仿真交易所通用实现。"""

from datetime import datetime
from typing import Optional

from exchange.base_engine import TradeOrder, TradeResult
from exchange.exchange_interface import StockExchange


class SimulatedExchangeBase(StockExchange):
    """仿真类交易所的通用逻辑。"""

    def __init__(self, init_cash: float = 100000.0, lot_size: float = 100.0, verbose: bool = False):
        super().__init__(init_cash=init_cash, lot_size=lot_size)
        self.verbose = verbose
        self.trade_count = 0
        self.connected = False

    def connect(self) -> bool:
        self.connected = True
        return True

    def disconnect(self) -> None:
        self.connected = False

    def buy(self, date: datetime, price: float, shares: Optional[float] = None) -> TradeResult:
        buy_shares = float(shares) if shares is not None else self.lot_size

        if buy_shares <= 0:
            if self.verbose:
                print(f"[{date.strftime('%Y-%m-%d')}] 买入失败：股数必须为正数 ({buy_shares})")
            return TradeResult(
                success=False,
                message=f"股数必须为正数：{buy_shares}",
                cash_after=self.account.cash,
                shares_after=self.account.position.shares,
            )

        cost = price * buy_shares
        if self.account.cash < cost:
            if self.verbose:
                print(f"[{date.strftime('%Y-%m-%d')}] 买入失败：资金不足 (需要 {cost:.2f}, 可用 {self.account.cash:.2f})")
            return TradeResult(
                success=False,
                message=f"资金不足：需要 {cost:.2f}，可用 {self.account.cash:.2f}",
                cash_after=self.account.cash,
                shares_after=self.account.position.shares,
            )

        self.account.cash -= cost
        self.account.position.shares += buy_shares
        self.account.position.total_cost += cost
        self.account.position.avg_cost = (
            self.account.position.total_cost / self.account.position.shares
            if self.account.position.shares > 0
            else 0.0
        )
        self.trade_count += 1

        order = TradeOrder(date=date, action="buy", price=price, shares=buy_shares)

        if self.verbose:
            print(
                f"[{date.strftime('%Y-%m-%d')}] 买入成功：价格 {price:.2f}, 数量 {buy_shares}, "
                f"成本 {cost:.2f}, 剩余现金 {self.account.cash:.2f}"
            )

        return TradeResult(
            success=True,
            message="买入成功",
            order=order,
            cash_after=self.account.cash,
            shares_after=self.account.position.shares,
        )

    def sell(self, date: datetime, price: float, shares: Optional[float] = None) -> TradeResult:
        sell_shares = float(shares) if shares is not None else self.lot_size

        if sell_shares <= 0:
            return TradeResult(
                success=False,
                message=f"股数必须为正数：{sell_shares}",
                cash_after=self.account.cash,
                shares_after=self.account.position.shares,
            )

        if self.account.position.shares < sell_shares:
            if self.verbose:
                print(
                    f"[{date.strftime('%Y-%m-%d')}] 卖出失败：持仓不足 "
                    f"(需要 {sell_shares}, 持有 {self.account.position.shares})"
                )
            return TradeResult(
                success=False,
                message=f"持仓不足：需要 {sell_shares}，持有 {self.account.position.shares}",
                cash_after=self.account.cash,
                shares_after=self.account.position.shares,
            )

        proceeds = price * sell_shares
        avg_cost = self.account.position.avg_cost
        cost_reduced = avg_cost * sell_shares
        realized_pl_this = (price - avg_cost) * sell_shares

        self.account.cash += proceeds
        self.account.position.shares -= sell_shares
        self.account.position.total_cost -= cost_reduced
        self.realized_pl += realized_pl_this
        self.trade_count += 1

        if self.account.position.shares > 0:
            self.account.position.avg_cost = self.account.position.total_cost / self.account.position.shares
        else:
            self.account.position.avg_cost = 0.0
            self.account.position.total_cost = 0.0

        order = TradeOrder(date=date, action="sell", price=price, shares=sell_shares)

        if self.verbose:
            print(
                f"[{date.strftime('%Y-%m-%d')}] 卖出成功：价格 {price:.2f}, 数量 {sell_shares}, "
                f"收入 {proceeds:.2f}, 本次盈亏 {realized_pl_this:.2f}, "
                f"累计盈亏 {self.realized_pl:.2f}, 现金 {self.account.cash:.2f}"
            )

        return TradeResult(
            success=True,
            message="卖出成功",
            order=order,
            cash_after=self.account.cash,
            shares_after=self.account.position.shares,
            realized_pl=realized_pl_this,
        )

    def print_daily_status(self, date: datetime, price_open: float, price_close: float,
                           action: Optional[str] = None) -> None:
        if not self.verbose:
            return

        pos = self.account.position
        market_value = pos.shares * price_close
        total_value = self.account.cash + market_value
        unrealized_pl = ((price_close - pos.avg_cost) * pos.shares) if pos.shares > 0 else 0.0

        action_str = f"操作: {action}" if action else "操作: 持有"

        print(
            f"[{date.strftime('%Y-%m-%d')}] "
            f"开盘: {price_open:.2f} | 收盘: {price_close:.2f} | "
            f"{action_str} | "
            f"持仓: {pos.shares} | "
            f"成本: {pos.avg_cost:.2f} | "
            f"现金: {self.account.cash:.2f} | "
            f"市值: {market_value:.2f} | "
            f"总值: {total_value:.2f} | "
            f"浮盈: {unrealized_pl:.2f}"
        )

    def get_real_time_price(self, symbol: str) -> float:
        _ = symbol
        raise NotImplementedError("仿真模式未接入实时行情，请在策略层传入价格")

    def cancel_order(self, order_id: str) -> bool:
        _ = order_id
        return False


# 向后兼容
SimulatedExchange = SimulatedExchangeBase
