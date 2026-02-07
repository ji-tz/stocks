import datetime
from typing import Any, Dict, List, Optional

from source.data_provider import get_data
from simulator.simulator_engine import SimulatorEngine


class Simulator:
    """通用模拟器：根据传入的决策器在时间序列上执行买/卖操作。

    决策器应实现 `decide(**kwargs)` 方法，返回 'buy' / 'sell' / None。

    现已基于新的 SimulatorEngine 架构重构，支持：
    - 更好的代码解耦
    - 详细的每日交易日志
    - 为实盘交易（real）做好接口准备
    """

    def __init__(self, lot_size: int = 100, init_cash: float = 100000.0, verbose: bool = False):
        """初始化模拟器

        Args:
            lot_size: 交易手数
            init_cash: 初始资金
            verbose: 是否打印详细的每日交易信息
        """
        self.lot_size = lot_size
        self.init_cash = float(init_cash)
        self.verbose = verbose

    def simulate(self, df, strategy, symbol: str = "", start_date: Optional[str] = None, end_date: Optional[str] = None, source: str = "auto", verbose: Optional[bool] = None) -> Dict[str, Any]:
        """执行模拟交易

        Args:
            df: 包含股票数据的DataFrame
            strategy: 决策策略对象，需实现decide()方法
            symbol: 股票代码
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            source: 数据源（可选）
            verbose: 是否打印详细信息（覆盖init时的设置）

        Returns:
            包含模拟结果的字典
        """
        if df is None:
            raise RuntimeError("需要传入数据 DataFrame 才能模拟")

        df = df.sort_values('date').reset_index(drop=True).copy()
        if df.empty:
            raise RuntimeError("数据为空，无法模拟")

        # 使用新的 SimulatorEngine
        use_verbose = verbose if verbose is not None else self.verbose
        engine = SimulatorEngine(init_cash=self.init_cash, lot_size=self.lot_size, verbose=use_verbose)

        history: List[Dict[str, Any]] = []
        trades_list: List[Dict[str, Any]] = []

        if use_verbose:
            print(f"\n{'='*100}")
            print(f"开始模拟交易 - 股票: {symbol if symbol else '未知'}")
            print(f"初始资金: {self.init_cash:.2f}, 交易手数: {self.lot_size}")
            print(f"数据范围: {df['date'].iloc[0].strftime('%Y-%m-%d')} 至 {df['date'].iloc[-1].strftime('%Y-%m-%d')}")
            print(f"{'='*100}\n")

        for _, row in df.iterrows():
            price_open = float(row['open'])
            price_close = float(row['close'])
            date = row['date']

            # 获取当前持仓信息
            pos = engine.get_position()
            avg_cost = pos.avg_cost

            # 调用策略决策
            action = None
            try:
                action = strategy.decide(
                    open_price=price_open,
                    close_price=price_close,
                    avg_cost=avg_cost,
                    shares=pos.shares,
                    date=date
                )
            except TypeError:
                # 向后兼容：尝试不带 date 参数
                action = strategy.decide(
                    open_price=price_open,
                    close_price=price_close,
                    avg_cost=avg_cost,
                    shares=pos.shares
                )

            # 执行交易
            trade_result = None
            if action == 'buy':
                trade_result = engine.buy(date=date, price=price_open)
                if trade_result.success:
                    trades_list.append({
                        'date': date.strftime('%Y-%m-%d'),
                        'action': 'buy',
                        'price': price_open,
                        'shares': self.lot_size,
                        'cash': round(trade_result.cash_after, 2),
                        'shares_after': trade_result.shares_after
                    })
            elif action == 'sell':
                trade_result = engine.sell(date=date, price=price_open)
                if trade_result.success:
                    trades_list.append({
                        'date': date.strftime('%Y-%m-%d'),
                        'action': 'sell',
                        'price': price_open,
                        'shares': self.lot_size,
                        'cash': round(trade_result.cash_after, 2),
                        'shares_after': trade_result.shares_after,
                        'realized_pl': round(engine.realized_pl, 4)
                    })

            # 打印每日状态（如果开启verbose）
            engine.print_daily_status(date, price_open, price_close, action)

            # 记录历史
            summary = engine.get_summary(price_close)
            history.append({
                'date': date.strftime('%Y-%m-%d'),
                'cash': summary['cash'],
                'shares': summary['shares'],
                'avg_cost': summary['avg_cost'],
                'last_price': round(price_close, 4),
                'market_value': summary['market_value'],
                'total_value': summary['total_value']
            })

        # 生成最终报告
        last_price = float(df.iloc[-1]['close'])
        final_summary = engine.get_summary(last_price)

        if use_verbose:
            print("\n" + "=" * 100)
            print("模拟交易结束")
            print("=" * 100)
            print(f"总交易次数: {engine.trade_count}")
            print(f"最终现金: {final_summary['cash']:.2f}")
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
            print(f"{'='*100}\n")

        return {
            'symbol': symbol,
            'start_date': df['date'].iloc[0].strftime('%Y-%m-%d'),
            'end_date': df['date'].iloc[-1].strftime('%Y-%m-%d'),
            'init_cash': self.init_cash,
            'cash': final_summary['cash'],
            'shares': final_summary['shares'],
            'last_price': last_price,
            'market_value': final_summary['market_value'],
            'realized_pl': final_summary['realized_pl'],
            'unrealized_pl': final_summary['unrealized_pl'],
            'total_value': final_summary['total_value'],
            'trades': engine.trade_count,
            'history': history,
            'trades_list': trades_list,
        }


def simulate_mean_cost(symbol: str = "600900",
                       start_date: str = "20250101",
                       end_date: Optional[str] = None,
                       lot_size: int = 100,
                       init_cash: float = 100000.0,
                       source: str = "auto") -> Dict[str, Any]:
    from solver.mean_cost_strategy import MeanCostDecision

    if end_date is None:
        end_date = datetime.datetime.today().strftime('%Y%m%d')

    df = get_data(symbol=symbol, source=source, start_date=start_date, end_date=end_date)
    if df is None:
        raise RuntimeError("未获取到数据，无法模拟")

    sim = Simulator(lot_size=lot_size, init_cash=init_cash)
    strategy = MeanCostDecision()
    return sim.simulate(df=df, strategy=strategy, symbol=symbol)


def simulate_sma(symbol: str = "600900",
                 df=None,
                 period: int = 20,
                 lot_size: int = 100,
                 init_cash: float = 100000.0):
    from solver.sma_strategy import SmaDecision

    if df is None:
        raise RuntimeError("需要传入数据 DataFrame 才能模拟")

    df = df.sort_values('date').reset_index(drop=True).copy()
    if df.empty:
        raise RuntimeError("数据为空，无法模拟 SMA")

    df['sma'] = df['close'].rolling(window=period, min_periods=1).mean()

    sim = Simulator(lot_size=lot_size, init_cash=init_cash)
    strategy = SmaDecision(period=period, df=df)
    return sim.simulate(df=df, strategy=strategy, symbol=symbol)
