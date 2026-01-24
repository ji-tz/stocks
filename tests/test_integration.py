import unittest
import pandas as pd
import akshare as ak
import backtrader as bt
from main import get_data
from solver.sma_strategy import SmaStrategy

class TestIntegration(unittest.TestCase):
    def test_backtrader_run(self):
        df = get_data()
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
        cerebro = bt.Cerebro()
        cerebro.adddata(data)
        cerebro.addstrategy(SmaStrategy)
        cerebro.broker.setcash(100000)
        cerebro.run()
        # 检查资金是否为float类型
        self.assertIsInstance(cerebro.broker.getvalue(), float)

if __name__ == "__main__":
    unittest.main()
