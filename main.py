import backtrader as bt
import pandas as pd
import akshare as ak
from solver.sma_strategy import SmaStrategy

# 获取长江电力历史数据（A股代码：600900）
def get_data():
    df = ak.stock_zh_a_hist(symbol="600900", period="daily", start_date="20200101", end_date="20231231", adjust="qfq")
    df = df[["日期", "开盘", "最高", "最低", "收盘", "成交量"]]
    df.columns = ["date", "open", "high", "low", "close", "volume"]
    df["date"] = pd.to_datetime(df["date"])
    return df

if __name__ == '__main__':
    cerebro = bt.Cerebro()
    df = get_data()
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
