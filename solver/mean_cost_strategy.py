import datetime
from typing import Dict, Any, List

from source.data_provider import get_data


def simulate_mean_cost(symbol: str = "600900",
                       start_date: str = "20250101",
                       end_date: str | None = None,
                       lot_size: int = 100,
                       init_cash: float = 100000.0,
                       source: str = "auto") -> Dict[str, Any]:
    """
    从 start_date 到 end_date（默认今天）按日开盘价模拟：
    - 每天开盘时：若持仓为0则买入1手；否则若开盘价 < 平均成本 -> 买入1手；若开盘价 > 平均成本 -> 卖出1手。
    - 使用简单的会计：买入时增加持仓并增加总成本；卖出时按平均成本计算已实现盈亏。

    返回字典包含初始资金、最终市值、现金、持仓、已实现盈亏、未实现盈亏、交易次数等。
    """
    if end_date is None:
        end_date = datetime.datetime.today().strftime('%Y%m%d')

    df = get_data(symbol=symbol, source=source, start_date=start_date, end_date=end_date)
    if df is None or df.empty:
        raise RuntimeError("未获取到数据，无法模拟")

    # 确保按日期升序
    df = df.sort_values('date').reset_index(drop=True)

    cash = float(init_cash)
    shares = 0
    total_cost = 0.0  # 持仓成本之和（用于计算平均成本）
    realized_pl = 0.0
    trades = 0

    history: List[Dict[str, Any]] = []
    trades_list: List[Dict[str, Any]] = []

    for _, row in df.iterrows():
        price = float(row['open'])
        date = row['date']
        # 当天开盘判断
        executed = None
        if shares == 0:
            # 建仓一手（若资金足够）
            cost = price * lot_size
            if cash >= cost:
                cash -= cost
                shares += lot_size
                total_cost += cost
                trades += 1
                executed = {'date': date.strftime('%Y-%m-%d'), 'action': 'buy', 'price': price, 'shares': lot_size, 'cash': cash, 'shares_after': shares}
        else:
            avg_cost = total_cost / shares
            if price < avg_cost:
                # 买入一手
                cost = price * lot_size
                if cash >= cost:
                    cash -= cost
                    shares += lot_size
                    total_cost += cost
                    trades += 1
                    executed = {'date': date.strftime('%Y-%m-%d'), 'action': 'buy', 'price': price, 'shares': lot_size, 'cash': cash, 'shares_after': shares}
            elif price > avg_cost:
                # 卖出一手
                if shares >= lot_size:
                    sell_proceeds = price * lot_size
                    cash += sell_proceeds
                    # 按平均成本减少成本基数
                    cost_reduced = avg_cost * lot_size
                    total_cost -= cost_reduced
                    realized_pl += (price - avg_cost) * lot_size
                    shares -= lot_size
                    trades += 1
                    executed = {'date': date.strftime('%Y-%m-%d'), 'action': 'sell', 'price': price, 'shares': lot_size, 'cash': cash, 'shares_after': shares, 'realized_pl': realized_pl}

        last_price = float(row['close'])
        market_value = shares * last_price
        avg_cost_now = (total_cost / shares) if shares > 0 else 0.0
        total_value_now = cash + market_value

        history.append({'date': date.strftime('%Y-%m-%d'), 'cash': round(cash, 2), 'shares': shares, 'avg_cost': round(avg_cost_now, 4), 'last_price': round(last_price, 4), 'market_value': round(market_value, 2), 'total_value': round(total_value_now, 2)})

        if executed:
            trades_list.append(executed)

    last_price = float(df.iloc[-1]['close'])
    market_value = shares * last_price
    unrealized_pl = (last_price - (total_cost / shares) if shares > 0 else 0.0) * shares if shares > 0 else 0.0
    total_value = cash + market_value

    return {
        'symbol': symbol,
        'start_date': df['date'].iloc[0].strftime('%Y-%m-%d'),
        'end_date': df['date'].iloc[-1].strftime('%Y-%m-%d'),
        'init_cash': init_cash,
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


if __name__ == '__main__':
    # 简单命令行运行示例
    import pprint
    res = simulate_mean_cost()
    pprint.pprint(res)
