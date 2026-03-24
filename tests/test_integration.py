import unittest
import pandas as pd
from unittest.mock import patch
import stocks


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

    @patch('stocks.get_data')
    def test_run_sma_backtest_integration(self, mock_get_data):
        mock_get_data.return_value = pd.DataFrame({
            'date': pd.date_range(end='2023-12-31', periods=60, freq='D'),
            'open': [100.0 + i for i in range(60)],
            'high': [101.0 + i for i in range(60)],
            'low': [99.0 + i for i in range(60)],
            'close': [100.0 + i for i in range(60)],
            'volume': [1000 + i * 10 for i in range(60)],
        })
        result = stocks.run_sma_backtest(
            symbol='600900',
            source='auto',
            start_date='20230101',
            end_date='20231231',
            period=20,
            lot_size=100,
            init_cash=100000.0,
        )
        self.assertEqual(result['symbol'], '600900')
        self.assertIn('total_value', result)
        self.assertIn('history', result)
        self.assertIn('trades_list', result)
        self.assertEqual(result['final_cash'], result['total_value'])


if __name__ == "__main__":
    unittest.main()
