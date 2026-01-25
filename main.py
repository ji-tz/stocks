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
    # 支持通过环境变量 DATA_SOURCE 指定数据来源：'akshare'|'baostock'|'auto' 或传入列表
    # 默认改为 'auto'，会按顺序尝试常见数据源并回退到本地缓存
    data_source = os.environ.get('DATA_SOURCE', 'auto')
    # 命令行参数可覆盖数据源，或使用 '--plot' 开启绘图
    plot_flag = os.environ.get('PLOT', '0').lower() in ('1', 'true', 'yes')
    cli_args = sys.argv[1:]
    for a in cli_args:
        if a == '--plot':
            plot_flag = True
        else:
            data_source = a

    print(f"使用数据源: {data_source}")
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
    if plot_flag:
        try:
            cerebro.plot()
        except Exception as e:
            print(f"绘图失败: {e}")
