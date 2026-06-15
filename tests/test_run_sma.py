import unittest
from unittest.mock import patch

import pandas as pd

import trader.stocks as stocks


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
class TestRunSMA(unittest.TestCase):
    @patch('trader.stocks.get_data')
    def test_run_sma_backtest_returns_unified_simulator_result(self, mock_get):
        df = make_mock_df(15)
        mock_get.return_value = df

        res = stocks.run_sma_backtest(symbol='600900', source='auto', start_date='20230101', end_date='20231231')
        self.assertIn('symbol', res)
        self.assertIn('init_cash', res)
        self.assertIn('cash', res)
        self.assertIn('total_value', res)
        self.assertIn('history', res)
        self.assertIn('trades_list', res)
        self.assertIn('final_cash', res)
        self.assertAlmostEqual(res['init_cash'], 100000.0)
        self.assertEqual(res['final_cash'], res['total_value'])

    @patch('trader.stocks.get_data')
    def test_run_sma_backtest_period_changes_result(self, mock_get):
        df = make_mock_df(30)
        closes = [
            100.0, 120.0, 80.0, 130.0, 70.0, 140.0, 60.0, 150.0, 50.0, 160.0,
            55.0, 155.0, 65.0, 145.0, 75.0, 135.0, 85.0, 125.0, 95.0, 115.0,
            105.0, 110.0, 100.0, 90.0, 80.0, 120.0, 140.0, 60.0, 150.0, 50.0,
        ]
        df['close'] = closes
        df['open'] = [value - 1.0 for value in closes]
        df['high'] = [value + 1.0 for value in closes]
        df['low'] = [value - 2.0 for value in closes]
        mock_get.return_value = df

        short_period_result = stocks.run_sma_backtest(
            symbol='600900', source='auto', start_date='20230101', end_date='20231231', period=5
        )
        long_period_result = stocks.run_sma_backtest(
            symbol='600900', source='auto', start_date='20230101', end_date='20231231', period=20
        )

        self.assertNotEqual(short_period_result['total_value'], long_period_result['total_value'])


if __name__ == '__main__':
    unittest.main()
