"""仿真交易所通用实现。"""

from datetime import datetime
from typing import Dict, Optional

from exchange.base_engine import TradeOrder, TradeResult
from exchange.exchange_interface import StockExchange


# ─── Market Detection ────────────────────────────────────────────────

# Default market rules keyed by market code
_MARKET_RULES: Dict[str, Dict] = {
    "A": {
        "lot_size": 100,
        "commission_pct": 0.00025,
        "stamp_duty_pct": 0.001,
        "t_plus_one": True,
    },
    "HK": {
        "lot_size": 100,
        "commission_pct": 0.0003,
        "stamp_duty_pct": 0.0013,
        "t_plus_one": False,
    },
    "BJ": {
        "lot_size": 100,
        "commission_pct": 0.00025,
        "stamp_duty_pct": 0.0,
        "t_plus_one": True,
    },
}


def detect_market(symbol: str) -> str:
    """Detect the market from a stock symbol.

    Args:
        symbol: Stock symbol (e.g. '600000', '000001.SH', '00700.HK', '830001').

    Returns:
        Market code: 'A' (沪深), 'HK' (港股), or 'BJ' (北证).
    """
    sym = symbol.strip().upper()
    if sym.endswith(".HK"):
        return "HK"
    if sym.startswith("8"):
        return "BJ"
    return "A"


# ─── SimulatedExchangeBase ───────────────────────────────────────────

class SimulatedExchangeBase(StockExchange):
    """仿真类交易所的通用逻辑。"""

    def __init__(self, init_cash: float = 100000.0, lot_size: float = 100.0, verbose: bool = False,
                 commission_pct: float = 0.00025, stamp_duty_pct: float = 0.001,
                 slippage_pct: float = 0.0, market: Optional[str] = None):
        """初始化仿真交易所。

        Args:
            init_cash: 初始资金。
            lot_size: 默认交易手数。
            verbose: 是否输出详细日志。
            commission_pct: 佣金比例（如 0.00025 表示万分之二点五）。
            stamp_duty_pct: 印花税比例（卖出时收取）。
            slippage_pct: 滑点比例。
            market: 市场代码（'A', 'HK', 'BJ'）。传入后将覆盖对应的默认费用/手数规则。
                    为 None 时保留调用方传入的 commission_pct / stamp_duty_pct / lot_size。
        """
        # Apply market-specific defaults when market is specified
        if market is not None:
            rules = SimulatedExchangeBase.market_rules(market)
            lot_size = rules["lot_size"]
            commission_pct = rules["commission_pct"]
            stamp_duty_pct = rules["stamp_duty_pct"]

        super().__init__(init_cash=init_cash, lot_size=lot_size,
                         commission_pct=commission_pct, stamp_duty_pct=stamp_duty_pct,
                         slippage_pct=slippage_pct)
        self.market = market or "A"
        self.verbose = verbose
        self.trade_count = 0
        self.connected = False

    @property
    def t_plus_one(self) -> bool:
        """是否实行 T+1 交易规则。"""
        rules = self.market_rules(self.market)
        return rules["t_plus_one"]

    @staticmethod
    def market_rules(market: str) -> Dict:
        """获取指定市场的交易规则。

        Args:
            market: 市场代码（'A', 'HK', 'BJ'）。

        Returns:
            包含 lot_size, commission_pct, stamp_duty_pct, t_plus_one 的字典。
        """
        m = market.upper()
        if m in _MARKET_RULES:
            return dict(_MARKET_RULES[m])
        return dict(_MARKET_RULES["A"])

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

        # 应用滑点：买入时价格向上偏移（更差的价格）
        effective_price = price * (1.0 + self.slippage_pct)
        cost_before_fees = effective_price * buy_shares
        commission = cost_before_fees * self.commission_pct
        total_cost = cost_before_fees + commission

        if self.account.cash < total_cost:
            if self.verbose:
                print(f"[{date.strftime('%Y-%m-%d')}] 买入失败：资金不足 (需要 {total_cost:.2f}, 可用 {self.account.cash:.2f})")
            return TradeResult(
                success=False,
                message=f"资金不足：需要 {total_cost:.2f}，可用 {self.account.cash:.2f}",
                cash_after=self.account.cash,
                shares_after=self.account.position.shares,
            )

        self.account.cash -= total_cost
        self.account.position.shares += buy_shares
        self.account.position.total_cost += cost_before_fees
        self.account.position.avg_cost = (
            self.account.position.total_cost / self.account.position.shares
            if self.account.position.shares > 0
            else 0.0
        )
        self.total_fees += commission
        self.trade_count += 1

        order = TradeOrder(date=date, action="buy", price=effective_price, shares=buy_shares)

        if self.verbose:
            print(
                f"[{date.strftime('%Y-%m-%d')}] 买入成功：价格 {effective_price:.2f}, 数量 {buy_shares}, "
                f"成本 {total_cost:.2f} (佣金 {commission:.2f}), "
                f"剩余现金 {self.account.cash:.2f}"
            )

        return TradeResult(
            success=True,
            message=f"买入成功 (佣金 ¥{commission:.2f})",
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

        # 应用滑点：卖出时价格向下偏移（更差的价格）
        effective_price = price * (1.0 - self.slippage_pct)
        proceeds_before_fees = effective_price * sell_shares
        commission = proceeds_before_fees * self.commission_pct
        stamp_duty = proceeds_before_fees * self.stamp_duty_pct
        total_fees_this = commission + stamp_duty
        net_proceeds = proceeds_before_fees - total_fees_this

        avg_cost = self.account.position.avg_cost
        cost_reduced = avg_cost * sell_shares
        # 已实现盈亏按净收入计算（已扣除费用）
        realized_pl_this = net_proceeds - cost_reduced

        self.account.cash += net_proceeds
        self.account.position.shares -= sell_shares
        self.account.position.total_cost -= cost_reduced
        self.realized_pl += realized_pl_this
        self.total_fees += total_fees_this
        self.trade_count += 1

        if self.account.position.shares > 0:
            self.account.position.avg_cost = self.account.position.total_cost / self.account.position.shares
        else:
            self.account.position.avg_cost = 0.0
            self.account.position.total_cost = 0.0

        order = TradeOrder(date=date, action="sell", price=effective_price, shares=sell_shares)

        if self.verbose:
            print(
                f"[{date.strftime('%Y-%m-%d')}] 卖出成功：价格 {effective_price:.2f}, 数量 {sell_shares}, "
                f"收入 {net_proceeds:.2f} (佣金 {commission:.2f}, 印花税 {stamp_duty:.2f}), "
                f"本次盈亏 {realized_pl_this:.2f}, "
                f"累计盈亏 {self.realized_pl:.2f}, 现金 {self.account.cash:.2f}"
            )

        return TradeResult(
            success=True,
            message=f"卖出成功 (佣金 ¥{commission:.2f}, 印花税 ¥{stamp_duty:.2f})",
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
