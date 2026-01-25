import datetime
from typing import Any, Dict, List, Optional

from source.data_provider import get_data


class Simulator:
    """通用模拟器：根据传入的决策器在时间序列上执行买/卖操作。

    决策器应实现 `decide(**kwargs)` 方法，返回 'buy' / 'sell' / None。
    """

    def __init__(self, lot_size: int = 100, init_cash: float = 100000.0):
        self.lot_size = lot_size
        self.init_cash = float(init_cash)

    def simulate(self, df, strategy, symbol: str = "", start_date: Optional[str] = None, end_date: Optional[str] = None, source: str = "auto") -> Dict[str, Any]:
        if df is None:
            raise RuntimeError("需要传入数据 DataFrame 才能模拟")

        df = df.sort_values('date').reset_index(drop=True).copy()
        if df.empty:
            raise RuntimeError("数据为空，无法模拟")

        cash = float(self.init_cash)
        shares = 0
        total_cost = 0.0
        realized_pl = 0.0
        trades = 0

        history: List[Dict[str, Any]] = []
        trades_list: List[Dict[str, Any]] = []

        for _, row in df.iterrows():
            price_open = float(row['open'])
            price_close = float(row['close'])
            date = row['date']

            # avg cost if any
            avg_cost = (total_cost / shares) if shares > 0 else 0.0

            # call strategy decide; strategy may use open/close/avg_cost/shares etc.
            action = None
            try:
                action = strategy.decide(open_price=price_open, close_price=price_close, avg_cost=avg_cost, shares=shares, date=date)
            except TypeError:
                # backward compatible: try without date
                action = strategy.decide(open_price=price_open, close_price=price_close, avg_cost=avg_cost, shares=shares)

            executed = None
            if action == 'buy':
                cost = price_open * self.lot_size
                if cash >= cost:
                    cash -= cost
                    shares += self.lot_size
                    total_cost += cost
                    trades += 1
                    executed = {'date': date.strftime('%Y-%m-%d'), 'action': 'buy', 'price': price_open, 'shares': self.lot_size, 'cash': round(cash,2), 'shares_after': shares}
            elif action == 'sell':
                if shares >= self.lot_size:
                    proceeds = price_open * self.lot_size
                    cash += proceeds
                    # reduce cost basis by avg_cost * lot
                    cost_reduced = avg_cost * self.lot_size
                    total_cost -= cost_reduced
                    realized_pl += (price_open - avg_cost) * self.lot_size
                    shares -= self.lot_size
                    trades += 1
                    executed = {'date': date.strftime('%Y-%m-%d'), 'action': 'sell', 'price': price_open, 'shares': self.lot_size, 'cash': round(cash,2), 'shares_after': shares, 'realized_pl': round(realized_pl,4)}

            market_value = shares * price_close
            avg_cost_now = (total_cost / shares) if shares > 0 else 0.0
            total_value_now = cash + market_value

            history.append({'date': date.strftime('%Y-%m-%d'), 'cash': round(cash, 2), 'shares': shares, 'avg_cost': round(avg_cost_now, 4), 'last_price': round(price_close, 4), 'market_value': round(market_value, 2), 'total_value': round(total_value_now, 2)})

            if executed:
                trades_list.append(executed)

        last_price = float(df.iloc[-1]['close'])
        market_value = shares * last_price
        unrealized_pl = ((last_price - (total_cost / shares)) * shares) if shares > 0 else 0.0
        total_value = cash + market_value

        return {
            'symbol': symbol,
            'start_date': df['date'].iloc[0].strftime('%Y-%m-%d'),
            'end_date': df['date'].iloc[-1].strftime('%Y-%m-%d'),
            'init_cash': self.init_cash,
            'cash': round(cash, 2),
            'shares': shares,
            'last_price': last_price,
            'market_value': round(market_value, 2),
            'realized_pl': round(realized_pl, 4),
            'unrealized_pl': round(unrealized_pl, 4),
            'total_value': round(total_value, 2),
            'trades': trades,
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
    import pandas as _pd

    if df is None:
        raise RuntimeError("需要传入数据 DataFrame 才能模拟")

    df = df.sort_values('date').reset_index(drop=True).copy()
    if df.empty:
        raise RuntimeError("数据为空，无法模拟 SMA")

    df['sma'] = df['close'].rolling(window=period, min_periods=1).mean()

    sim = Simulator(lot_size=lot_size, init_cash=init_cash)
    strategy = SmaDecision(period=period, df=df)
    return sim.simulate(df=df, strategy=strategy, symbol=symbol)
