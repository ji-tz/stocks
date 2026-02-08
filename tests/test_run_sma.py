import sys
import types
import unittest
from unittest.mock import patch

import pandas as pd

import stocks


def make_mock_df(n=10):
    dates = pd.date_range(end="2023-12-31", periods=n, freq="D")
    data = {
        "date": dates,
        "open": [100.0 + i for i in range(n)],
        "high": [101.0 + i for i in range(n)],
        "low": [99.0 + i for i in range(n)],
        "close": [100.0 + i for i in range(n)],
        "volume": [1000 + i * 10 for i in range(n)],
    }
    return pd.DataFrame(data)


class FakeBroker:
    def __init__(self):
        self._value = 100000.0

    def setcash(self, v):
        self._value = float(v)

    def getvalue(self):
        return float(self._value)


class FakeCerebro:
    def __init__(self):
        self._data = []
        self._strategies = []
        self.broker = FakeBroker()

    def adddata(self, d):
        self._data.append(d)

    def addstrategy(self, s):
        self._strategies.append(s)

    def run(self):
        # simulate some profit
        self.broker._value += 1234.5


class FakeFeeds:
    class PandasData:
        def __init__(self, dataname=None, **kwargs):
            self.dataname = dataname


class TestRunSMA(unittest.TestCase):
    @patch('source.data_provider.get_data')
    def test_run_sma_backtest_with_fake_backtrader(self, mock_get):
        # prepare data
        df = make_mock_df(15)
        mock_get.return_value = df

        # inject fake backtrader module
        fake_bt = types.ModuleType('backtrader')
        fake_bt.Cerebro = FakeCerebro
        fake_bt.feeds = FakeFeeds()
        sys.modules['backtrader'] = fake_bt

        try:
            # pass explicit date range to ensure it's handled
            res = stocks.run_sma_backtest(symbol='600900', source='auto', start_date='20230101', end_date='20231231')
            self.assertIn('symbol', res)
            self.assertIn('init_cash', res)
            self.assertIn('final_cash', res)
            self.assertAlmostEqual(res['init_cash'], 100000.0)
            self.assertTrue(res['final_cash'] >= res['init_cash'])
        finally:
            # cleanup injected module
            sys.modules.pop('backtrader', None)


if __name__ == '__main__':
    unittest.main()
