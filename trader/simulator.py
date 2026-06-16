import datetime
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from exchange.source.data_provider import get_data
from trader.clock import BacktestClock
from exchange.backtest.exchange import BacktestExchange


SUPPORTED_TRADE_PRICE_FIELDS = ("open", "close", "high", "low")


def _resolve_trade_price(row, trade_price: str) -> float:
    """按交易时点字段获取本次成交价。"""
    if trade_price not in SUPPORTED_TRADE_PRICE_FIELDS:
        raise ValueError(f"不支持的交易价格字段: {trade_price}")
    return float(row[trade_price])


@dataclass
class PendingOrder:
    """预约单（条件单）定义。"""

    action: str
    due_bar_index: int
    tag: str = ""


class BacktestExchangeRunner:
    """回测交易所执行器：根据传入决策器在时钟驱动下执行买卖。"""

    def __init__(self, lot_size: float = 100.0, init_cash: float = 100000.0, verbose: bool = False):
        self.lot_size = lot_size
        self.init_cash = float(init_cash)
        self.verbose = verbose

    @staticmethod
    def _normalize_granularity(granularity: str) -> str:
        g = str(granularity).strip().lower()
        aliases = {
            "d": "1d",
            "day": "1d",
            "daily": "1d",
            "1day": "1d",
            "h": "1h",
            "hour": "1h",
            "hourly": "1h",
            "1hour": "1h",
        }
        if g in aliases:
            return aliases[g]
        if g in ("1d", "1h"):
            return g
        raise RuntimeError(f"不支持的仿真粒度: {granularity}，当前仅支持 1d / 1h")

    @staticmethod
    def _date_key(value: Any) -> str:
        if hasattr(value, "strftime"):
            return value.strftime("%Y-%m-%d")
        return str(value)[:10]

    def _setup_base_position(
        self,
        engine: BacktestExchange,
        first_date: Any,
        first_price: float,
        base_position_lots: int,
    ) -> float:
        if base_position_lots <= 0:
            return 0.0

        base_shares = float(base_position_lots * self.lot_size)
        cost = first_price * base_shares
        if engine.account.cash < cost:
            raise RuntimeError(
                f"底仓初始化失败：需要资金 {cost:.2f}，可用资金 {engine.account.cash:.2f}，"
                f"请提高初始资金或降低 base_position_lots"
            )

        engine.account.cash -= cost
        engine.account.position.shares = base_shares
        engine.account.position.total_cost = cost
        engine.account.position.avg_cost = first_price

        if self.verbose:
            print(
                f"[底仓初始化] 日期: {self._date_key(first_date)} | 股数: {base_shares} | "
                f"成本价: {first_price:.4f} | 占用资金: {cost:.2f}"
            )
        return base_shares

    def run(
        self,
        df,
        strategy,
        symbol: str = "",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        source: str = "auto",
        verbose: Optional[bool] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        trade_price: str = "open",
        granularity: str = "1d",
        enable_scheduled_orders: bool = False,
        enforce_t_plus_one: bool = False,
        require_base_position_for_t_plus_one_intraday: bool = False,
        base_position_lots: Optional[int] = None,
        mode: str = "backtest",
    ) -> Dict[str, Any]:
        """执行回测。"""
        if mode != "backtest":
            raise RuntimeError("当前执行器仅支持 backtest 模式，其它模式不运行")

        if df is None:
            raise RuntimeError("需要传入数据 DataFrame 才能模拟")

        _ = start_date, end_date, source

        granularity = self._normalize_granularity(granularity)

        df = df.sort_values("date").reset_index(drop=True).copy()
        if df.empty:
            raise RuntimeError("数据为空，无法模拟")

        use_verbose = verbose if verbose is not None else self.verbose
        engine = BacktestExchange(init_cash=self.init_cash, lot_size=self.lot_size, verbose=use_verbose)

        resolved_base_position_lots = base_position_lots
        if require_base_position_for_t_plus_one_intraday and resolved_base_position_lots is None:
            resolved_base_position_lots = 2
        if resolved_base_position_lots is None:
            resolved_base_position_lots = 0

        if require_base_position_for_t_plus_one_intraday and enforce_t_plus_one and granularity == "1h":
            if resolved_base_position_lots <= 0:
                raise RuntimeError(
                    "A股 T+1 规则下，日内策略需要底仓才能执行当日卖出。"
                    "请设置 base_position_lots（默认建议 2 手）。"
                )

        first_trade_price = _resolve_trade_price(df.iloc[0], trade_price)
        base_position_shares = self._setup_base_position(
            engine=engine,
            first_date=df.iloc[0]["date"],
            first_price=first_trade_price,
            base_position_lots=resolved_base_position_lots,
        )

        history: List[Dict[str, Any]] = []
        trades_list: List[Dict[str, Any]] = []
        pending_orders: List[PendingOrder] = []
        min_cash = engine.get_cash()
        today_bought_shares: Dict[str, float] = {}

        if use_verbose:
            print(f"\n{'=' * 100}")
            print(f"开始回测交易 - 股票: {symbol if symbol else '未知'}")
            print(f"初始资金: {self.init_cash:.2f}, 交易手数: {self.lot_size}, 粒度: {granularity}")
            print(
                f"数据范围: {df['date'].iloc[0].strftime('%Y-%m-%d')} 至 "
                f"{df['date'].iloc[-1].strftime('%Y-%m-%d')}"
            )
            print("时钟: BacktestClock")
            print(f"{'=' * 100}\n")

        def schedule_order(action: str, after_bars: Optional[int] = None,
                           after_hours: Optional[int] = None, tag: str = "") -> None:
            if not enable_scheduled_orders:
                raise RuntimeError("当前回测未启用预约单功能，请设置 enable_scheduled_orders=True")
            if action not in ("buy", "sell"):
                raise RuntimeError(f"预约单 action 非法: {action}")

            wait_bars = 0
            if after_bars is not None:
                wait_bars = int(after_bars)
            elif after_hours is not None:
                if granularity != "1h":
                    raise RuntimeError("after_hours 仅在 granularity='1h' 时可用")
                wait_bars = int(after_hours)

            if wait_bars < 0:
                raise RuntimeError("预约单延迟不能为负数")

            due = current_idx + wait_bars
            pending_orders.append(PendingOrder(action=action, due_bar_index=due, tag=tag))

        def execute_trade(
            action: str,
            date: Any,
            execution_price: float,
            action_source: str,
            desired_shares: Optional[float] = None,
        ) -> None:
            nonlocal min_cash
            date_key = self._date_key(date)

            if action == "buy":
                buy_shares = None
                if desired_shares is not None:
                    buy_shares = float(desired_shares)
                elif hasattr(strategy, "calculate_shares") and callable(getattr(strategy, "calculate_shares")):
                    calculate_shares = getattr(strategy, "calculate_shares")
                    for calculate_kwargs in (
                        {
                            "price": execution_price,
                            "lot_size": self.lot_size,
                            "cash": engine.get_cash(),
                            "position_shares": float(engine.get_position().shares),
                        },
                        {
                            "price": execution_price,
                            "lot_size": self.lot_size,
                        },
                    ):
                        try:
                            buy_shares = float(calculate_shares(**calculate_kwargs))
                            break
                        except TypeError:
                            continue

                if buy_shares is not None and buy_shares <= 0:
                    return

                result = engine.buy(date=date, price=execution_price, shares=buy_shares)
                if result.success:
                    actual_shares = float(buy_shares) if buy_shares is not None else float(self.lot_size)
                    today_bought_shares[date_key] = today_bought_shares.get(date_key, 0.0) + actual_shares
                    trades_list.append(
                        {
                            "date": date.strftime("%Y-%m-%d"),
                            "action": "buy",
                            "price": round(execution_price, 4),
                            "trade_price_field": trade_price,
                            "shares": actual_shares,
                            "cash": round(result.cash_after, 2),
                            "shares_after": result.shares_after,
                            "source": action_source,
                        }
                    )
                return

            if action == "sell":
                sell_shares = float(self.lot_size)
                if desired_shares is not None:
                    sell_shares = float(desired_shares)
                elif hasattr(strategy, "calculate_sell_shares") and callable(getattr(strategy, "calculate_sell_shares")):
                    calculate_sell_shares = getattr(strategy, "calculate_sell_shares")
                    for calculate_kwargs in (
                        {
                            "price": execution_price,
                            "lot_size": self.lot_size,
                            "position_shares": float(engine.get_position().shares),
                            "cash": engine.get_cash(),
                        },
                        {
                            "price": execution_price,
                            "lot_size": self.lot_size,
                            "position_shares": float(engine.get_position().shares),
                        },
                    ):
                        try:
                            sell_shares = float(calculate_sell_shares(**calculate_kwargs))
                            break
                        except TypeError:
                            continue

                if sell_shares <= 0:
                    return

                if enforce_t_plus_one:
                    sellable_shares = float(engine.get_position().shares) - today_bought_shares.get(date_key, 0.0)
                    if sellable_shares < sell_shares:
                        if use_verbose:
                            print(
                                f"[{date.strftime('%Y-%m-%d')}] 卖出拦截（T+1）："
                                f"可卖 {sellable_shares} 股，小于计划卖出股数 {sell_shares}"
                            )
                        return

                result = engine.sell(date=date, price=execution_price, shares=sell_shares)
                if result.success:
                    trades_list.append(
                        {
                            "date": date.strftime("%Y-%m-%d"),
                            "action": "sell",
                            "price": round(execution_price, 4),
                            "trade_price_field": trade_price,
                            "shares": sell_shares,
                            "cash": round(result.cash_after, 2),
                            "shares_after": result.shares_after,
                            "realized_pl": round(engine.realized_pl, 4),
                            "source": action_source,
                        }
                    )
                return

            raise RuntimeError(f"不支持的交易动作: {action}")

        clock = BacktestClock(df=df, granularity=granularity)
        for tick in clock.iter_ticks():
            current_idx = tick.bar_index
            row = tick.row

            if progress_callback:
                try:
                    progress_callback(tick.bar_index, tick.total_bars)
                except Exception as e:
                    if use_verbose:
                        print(f"警告: 进度回调失败 - {e}")

            price_open = float(row["open"])
            price_close = float(row["close"])
            execution_price = _resolve_trade_price(row, trade_price)
            date = row["date"]

            due_orders = [o for o in pending_orders if o.due_bar_index <= current_idx]
            if due_orders:
                pending_orders = [o for o in pending_orders if o.due_bar_index > current_idx]
                for order in due_orders:
                    execute_trade(
                        order.action,
                        date,
                        execution_price,
                        action_source=f"scheduled:{order.tag}" if order.tag else "scheduled",
                    )

            pos = engine.get_position()
            avg_cost = pos.avg_cost

            action = None
            decision_kwargs_chain = [
                {
                    "open_price": price_open,
                    "close_price": price_close,
                    "avg_cost": avg_cost,
                    "shares": pos.shares,
                    "date": date,
                    "cash": engine.get_cash(),
                    "trade_price": execution_price,
                    "trade_price_field": trade_price,
                    "schedule_order": schedule_order,
                    "granularity": granularity,
                    "bar_index": tick.bar_index,
                },
                {
                    "open_price": price_open,
                    "close_price": price_close,
                    "avg_cost": avg_cost,
                    "shares": pos.shares,
                    "date": date,
                },
                {
                    "open_price": price_open,
                    "close_price": price_close,
                    "avg_cost": avg_cost,
                    "shares": pos.shares,
                },
            ]

            action_raw = None
            for decision_kwargs in decision_kwargs_chain:
                try:
                    action_raw = strategy.decide(**decision_kwargs)
                    break
                except TypeError:
                    continue

            action = action_raw
            desired_shares = None
            if isinstance(action_raw, dict):
                action = action_raw.get("action")
                desired_shares_raw = action_raw.get("shares")
                if desired_shares_raw is not None:
                    try:
                        desired_shares = float(desired_shares_raw)
                    except Exception:
                        desired_shares = None
                schedule_orders = action_raw.get("schedule_orders")
                if schedule_orders:
                    if not enable_scheduled_orders:
                        raise RuntimeError("策略返回了预约单，但当前未启用 enable_scheduled_orders")
                    for order_cfg in schedule_orders:
                        schedule_order(
                            action=order_cfg.get("action"),
                            after_bars=order_cfg.get("after_bars"),
                            after_hours=order_cfg.get("after_hours"),
                            tag=order_cfg.get("tag", ""),
                        )

            if action in ("buy", "sell"):
                execute_trade(
                    action,
                    date,
                    execution_price,
                    action_source="strategy",
                    desired_shares=desired_shares,
                )

            engine.print_daily_status(date, price_open, price_close, action)

            summary = engine.get_summary(price_close)
            history.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "cash": summary["cash"],
                    "shares": summary["shares"],
                    "avg_cost": summary["avg_cost"],
                    "last_price": round(price_close, 4),
                    "market_value": summary["market_value"],
                    "total_value": summary["total_value"],
                }
            )
            min_cash = min(min_cash, summary["cash"])

        last_price = float(df.iloc[-1]["close"])
        final_summary = engine.get_summary(last_price)
        max_capital_used = self.init_cash - min_cash

        if use_verbose:
            print("\n" + "=" * 100)
            print("回测交易结束")
            print("=" * 100)
            print(f"总交易次数: {engine.trade_count}")
            print(f"最终现金: {final_summary['cash']:.2f}")
            print(f"最小现金余额: {min_cash:.2f}")
            print(f"最大占用资金: {max_capital_used:.2f}")
            print(f"最终持仓: {final_summary['shares']} 股")
            print(f"平均成本: {final_summary['avg_cost']:.4f}")
            print(f"最新价格: {last_price:.4f}")
            print(f"市值: {final_summary['market_value']:.2f}")
            print(f"总资产: {final_summary['total_value']:.2f}")
            print(f"已实现盈亏: {final_summary['realized_pl']:.4f}")
            print(f"未实现盈亏: {final_summary['unrealized_pl']:.4f}")
            total_pl = final_summary['realized_pl'] + final_summary['unrealized_pl']
            print(f"总盈亏: {total_pl:.4f}")
            print(f"收益率: {(total_pl / self.init_cash * 100):.2f}%")
            print(f"{'=' * 100}\n")

        # ---- 计算标准化 metrics ----
        total_pl = final_summary["realized_pl"] + final_summary["unrealized_pl"]
        total_return_rate = total_pl / self.init_cash if self.init_cash else 0

        # 年化收益率
        annualized_return = 0.0
        try:
            from datetime import datetime
            s = datetime.strptime(df["date"].iloc[0].strftime("%Y-%m-%d"), "%Y-%m-%d")
            e = datetime.strptime(df["date"].iloc[-1].strftime("%Y-%m-%d"), "%Y-%m-%d")
            days = (e - s).days
            if days > 0:
                annualized_return = (
                    (final_summary["total_value"] / self.init_cash) ** (365.0 / days) - 1
                )
        except (ValueError, ZeroDivisionError):
            annualized_return = 0.0

        # 最大回撤
        max_drawdown = 0.0
        if history:
            peak = max(history[0].get("total_value", self.init_cash), self.init_cash)
            for h in history:
                tv = h.get("total_value", self.init_cash)
                if tv > peak:
                    peak = tv
                drawdown = (peak - tv) / peak if peak > 0 else 0
                if drawdown > max_drawdown:
                    max_drawdown = drawdown

        # 夏普比率（近似）
        sharpe_ratio = 0.0
        if len(history) >= 2:
            try:
                import statistics
                daily_returns = []
                for i in range(1, len(history)):
                    prev_tv = history[i - 1].get("total_value", self.init_cash)
                    curr_tv = history[i].get("total_value", self.init_cash)
                    if prev_tv > 0:
                        daily_returns.append((curr_tv - prev_tv) / prev_tv)
                if daily_returns:
                    avg = statistics.mean(daily_returns)
                    std = statistics.stdev(daily_returns) if len(daily_returns) > 1 else 0
                    if std > 0:
                        sharpe_ratio = (avg * 252 - 0.02) / (std * (252 ** 0.5))
            except (ValueError, ZeroDivisionError, IndexError):
                sharpe_ratio = 0.0

        metrics = {
            "total_return_rate": round(total_return_rate, 4),
            "annualized_return": round(annualized_return, 4),
            "max_drawdown": round(max_drawdown, 4),
            "sharpe_ratio": round(sharpe_ratio, 4),
            "total_pl": round(total_pl, 2),
            "final_value": round(final_summary["total_value"], 2),
        }

        return {
            "symbol": symbol,
            "start_date": df["date"].iloc[0].strftime("%Y-%m-%d"),
            "end_date": df["date"].iloc[-1].strftime("%Y-%m-%d"),
            "init_cash": self.init_cash,
            "cash": final_summary["cash"],
            "shares": final_summary["shares"],
            "last_price": last_price,
            "market_value": final_summary["market_value"],
            "realized_pl": final_summary["realized_pl"],
            "unrealized_pl": final_summary["unrealized_pl"],
            "total_value": final_summary["total_value"],
            "trades": engine.trade_count,
            "trade_price_field": trade_price,
            "max_capital_used": round(max_capital_used, 2),
            "min_cash": round(min_cash, 2),
            "history": history,
            "trades_list": trades_list,
            "metrics": metrics,
            "pending_orders_left": len(pending_orders),
            "granularity": granularity,
            "enforce_t_plus_one": enforce_t_plus_one,
            "base_position_lots": resolved_base_position_lots,
            "base_position_shares": base_position_shares,
            "clock_type": "backtest",
            "mode": mode,
        }

    def simulate(
        self,
        df,
        strategy,
        symbol: str = "",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        source: str = "auto",
        verbose: Optional[bool] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        trade_price: str = "open",
        granularity: str = "1d",
        enable_scheduled_orders: bool = False,
        enforce_t_plus_one: bool = False,
        require_base_position_for_t_plus_one_intraday: bool = False,
        base_position_lots: Optional[int] = None,
        mode: str = "backtest",
    ) -> Dict[str, Any]:
        """兼容旧命名：simulate 等价于 run。"""
        return self.run(
            df=df,
            strategy=strategy,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            source=source,
            verbose=verbose,
            progress_callback=progress_callback,
            trade_price=trade_price,
            granularity=granularity,
            enable_scheduled_orders=enable_scheduled_orders,
            enforce_t_plus_one=enforce_t_plus_one,
            require_base_position_for_t_plus_one_intraday=require_base_position_for_t_plus_one_intraday,
            base_position_lots=base_position_lots,
            mode=mode,
        )


class Simulator(BacktestExchangeRunner):
    """兼容别名：等价于 BacktestExchangeRunner。"""


def simulate_mean_cost(
    symbol: str = "600900",
    start_date: str = "20250101",
    end_date: Optional[str] = None,
    lot_size: float = 100.0,
    init_cash: float = 100000.0,
    source: str = "auto",
    progress_callback: Optional[Callable[[int, int], None]] = None,
    trade_price: str = "open",
) -> Dict[str, Any]:
    from strategy.mean_cost_strategy import MeanCostDecision

    if end_date is None:
        end_date = datetime.datetime.today().strftime("%Y%m%d")

    df = get_data(symbol=symbol, source=source, start_date=start_date, end_date=end_date)
    if df is None:
        raise RuntimeError("未获取到数据，无法模拟")

    sim = Simulator(lot_size=lot_size, init_cash=init_cash)
    strategy = MeanCostDecision()
    return sim.simulate(
        df=df,
        strategy=strategy,
        symbol=symbol,
        progress_callback=progress_callback,
        trade_price=trade_price,
    )


def simulate_sma(
    symbol: str = "600900",
    df=None,
    period: int = 20,
    lot_size: float = 100.0,
    init_cash: float = 100000.0,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    trade_price: str = "open",
):
    from strategy.sma_strategy import SmaDecision

    if df is None:
        raise RuntimeError("需要传入数据 DataFrame 才能模拟")

    df = df.sort_values("date").reset_index(drop=True).copy()
    if df.empty:
        raise RuntimeError("数据为空，无法模拟 SMA")

    df["sma"] = df["close"].rolling(window=period, min_periods=1).mean()

    sim = Simulator(lot_size=lot_size, init_cash=init_cash)
    strategy = SmaDecision(period=period, df=df)
    return sim.simulate(
        df=df,
        strategy=strategy,
        symbol=symbol,
        progress_callback=progress_callback,
        trade_price=trade_price,
    )


def simulate_fixed_amount(
    symbol: str = "600900",
    start_date: str = "20250101",
    end_date: Optional[str] = None,
    fixed_amount: float = 1000.0,
    lot_size: float = 100.0,
    init_cash: float = 100000.0,
    source: str = "auto",
    verbose: bool = False,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    trade_price: str = "open",
) -> Dict[str, Any]:
    """运行定投策略回测。"""
    from strategy.fixed_amount_strategy import FixedAmountDecision

    if end_date is None:
        end_date = datetime.datetime.today().strftime("%Y%m%d")

    df = get_data(symbol=symbol, source=source, start_date=start_date, end_date=end_date)
    if df is None:
        raise RuntimeError("未获取到数据，无法模拟")

    sim = Simulator(lot_size=lot_size, init_cash=init_cash, verbose=verbose)
    strategy = FixedAmountDecision(fixed_amount=fixed_amount)
    return sim.simulate(
        df=df,
        strategy=strategy,
        symbol=symbol,
        progress_callback=progress_callback,
        trade_price=trade_price,
    )


def simulate_signal_template(
    symbol: str,
    df,
    strategy,
    lot_size: float = 100.0,
    init_cash: float = 100000.0,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    trade_price: str = "open",
) -> Dict[str, Any]:
    """运行模板化信号策略回测。"""
    if df is None:
        raise RuntimeError("需要传入数据 DataFrame 才能模拟")

    sim = Simulator(lot_size=lot_size, init_cash=init_cash)
    return sim.simulate(
        df=df,
        strategy=strategy,
        symbol=symbol,
        progress_callback=progress_callback,
        trade_price=trade_price,
    )
