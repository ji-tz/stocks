import backtrader as bt
import pandas as pd
import os
import sys
from solver.sma_strategy import SmaStrategy
from source.data_provider import get_data

# 获取长江电力历史数据（A股代码：600900）
# 数据来源使用统一的 data_provider.get_data，支持多渠道（例如 akshare / baostock）

if __name__ == '__main__':
    cerebro = bt.Cerebro()
    # 支持通过环境变量 DATA_SOURCE 指定数据来源：'akshare' 或 'baostock'
    data_source = os.environ.get('DATA_SOURCE', 'akshare')
    # 支持通过命令行传参覆盖（例如: python main.py baostock）
    if len(sys.argv) > 1:
        data_source = sys.argv[1]

    df = get_data(symbol="600900", source=data_source)
    # 只保留回测所需的字段，去除多余列
    df = df[["date", "open", "high", "low", "close", "volume"]]
    data = bt.feeds.PandasData(
        dataname=df,
        datetime="date",
        open="open",
        high="high",
        low="low",
        close="close",
        volume="volume",
        openinterest=None
    )
    cerebro.adddata(data)
    cerebro.addstrategy(SmaStrategy)
    cerebro.broker.setcash(100000)
    print('初始资金: %.2f' % cerebro.broker.getvalue())
    cerebro.run()
    print('回测后资金: %.2f' % cerebro.broker.getvalue())
    cerebro.plot()
