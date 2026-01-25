import unittest
import pandas as pd
from unittest.mock import patch
import backtrader as bt
from main import get_data
from solver.sma_strategy import SmaStrategy


class TestIntegration(unittest.TestCase):
    def make_mock_df(self, n=60):
        dates = pd.date_range(end="2023-12-31", periods=n, freq="D")
        data = {
            "日期": dates.strftime("%Y-%m-%d"),
            "开盘": [100.0 + i for i in range(n)],
            "最高": [101.0 + i for i in range(n)],
            "最低": [99.0 + i for i in range(n)],
            "收盘": [100.0 + i for i in range(n)],
            "成交量": [1000 + i * 10 for i in range(n)],
        }
        return pd.DataFrame(data)

    @patch('source.data_provider.ak.stock_zh_a_hist')
    def test_backtrader_run(self, mock_hist):
        mock_hist.return_value = self.make_mock_df(60)
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
