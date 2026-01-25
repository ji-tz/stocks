import unittest
from unittest.mock import patch

from gui.web import app
import pandas as pd


class TestGuiRoutes(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_index_get(self):
        rv = self.client.get('/')
        self.assertEqual(rv.status_code, 200)
        # page title should be present (Chinese)
        body = rv.data.decode('utf-8')
        self.assertIn('量化回测平台', body)
        # ensure client-side validation script present
        self.assertIn('function validateDates', body)

    @patch('stocks.get_data')
    @patch('stocks.run_mean_cost')
    def test_run_mean_cost_post(self, mock_mean, mock_get):
        # return a minimal dataframe required by the view
        dates = pd.date_range(end="2023-12-31", periods=5, freq="D")
        df = pd.DataFrame({
            'date': dates, 'open': [100.0+i for i in range(5)], 'high': [101.0+i for i in range(5)],
            'low': [99.0+i for i in range(5)], 'close': [100.0+i for i in range(5)], 'volume': [1000+i*10 for i in range(5)]
        })
        mock_get.return_value = df
        mock_mean.return_value = {
            'symbol': '600900', 'start_date': '2023-01-01', 'end_date': '2023-01-10', 'init_cash': 100000.0,
            'trades': 1, 'total_value': 100000.0, 'realized_pl': 0.0, 'unrealized_pl': 0.0, 'history': [], 'trades_list': []
        }
        rv = self.client.post('/run', data={'symbol': '600900', 'strategy': 'mean_cost', 'start': '20230101', 'end': '20231231'})
        self.assertEqual(rv.status_code, 200)
        self.assertIn('平均成本策略回测结果', rv.data.decode('utf-8'))
        # ensure backend was queried with date range
        mock_get.assert_called()

    @patch('stocks.get_data')
    @patch('stocks.run_sma_backtest')
    def test_run_sma_post(self, mock_sma, mock_get):
        dates = pd.date_range(end="2023-12-31", periods=5, freq="D")
        df = pd.DataFrame({
            'date': dates, 'open': [100.0+i for i in range(5)], 'high': [101.0+i for i in range(5)],
            'low': [99.0+i for i in range(5)], 'close': [100.0+i for i in range(5)], 'volume': [1000+i*10 for i in range(5)]
        })
        mock_get.return_value = df
        mock_sma.return_value = {'symbol': '600900', 'start_date': '2023-01-01', 'end_date': '2023-01-10', 'init_cash': 100000.0, 'final_cash': 100500.0}
        rv = self.client.post('/run', data={'symbol': '600900', 'strategy': 'sma', 'start': '20230101', 'end': '20231231'})
        self.assertEqual(rv.status_code, 200)
        self.assertIn('回测结果', rv.data.decode('utf-8'))
        mock_get.assert_called()

    def test_run_post_invalid_date_shows_error(self):
        rv = self.client.post('/run', data={'symbol': '600900', 'strategy': 'sma', 'start': 'invalid-date'})
        self.assertEqual(rv.status_code, 200)
        self.assertIn('发生错误', rv.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
