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
        # ensure strategy cards are present
        self.assertIn('SMA 策略', body)
        self.assertIn('均值成本策略', body)
        self.assertIn('定投策略', body)
        # ensure navigation links are present
        self.assertIn('/strategy/sma', body)
        self.assertIn('/strategy/mean_cost', body)
        self.assertIn('/strategy/fixed_amount', body)
        # ensure history link is present
        self.assertIn('历史记录', body)
        self.assertIn('/history', body)

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
            'trades': 1, 'total_value': 100000.0, 'market_value': 20000.0, 'realized_pl': 0.0, 'unrealized_pl': 0.0, 'history': [], 'trades_list': []
        }
        rv = self.client.post('/run', data={'symbol': '600900', 'strategy': 'mean_cost', 'start': '20230101', 'end': '20231231'})
        self.assertEqual(rv.status_code, 200)
        body = rv.data.decode('utf-8')
        self.assertIn('平均成本策略回测结果', body)
        # Verify the new "总共动用资金" field is displayed with correct value
        self.assertIn('总共动用资金', body)
        # Check that the market value appears in the correct context (near the label)
        self.assertIn('总共动用资金：</strong> 20000.00', body)
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

    def test_strategy_sma_get(self):
        """测试 SMA 策略配置页面"""
        rv = self.client.get('/strategy/sma')
        self.assertEqual(rv.status_code, 200)
        body = rv.data.decode('utf-8')
        self.assertIn('SMA 策略回测', body)
        self.assertIn('策略说明', body)
        self.assertIn('SMA 周期', body)
        self.assertIn('function validateDates', body)

    def test_strategy_mean_cost_get(self):
        """测试均值成本策略配置页面"""
        rv = self.client.get('/strategy/mean_cost')
        self.assertEqual(rv.status_code, 200)
        body = rv.data.decode('utf-8')
        self.assertIn('均值成本策略回测', body)
        self.assertIn('策略说明', body)
        self.assertIn('逢低加仓', body)
        self.assertIn('function validateDates', body)

    def test_strategy_fixed_amount_get(self):
        """测试定投策略配置页面"""
        rv = self.client.get('/strategy/fixed_amount')
        self.assertEqual(rv.status_code, 200)
        body = rv.data.decode('utf-8')
        self.assertIn('定投策略回测', body)
        self.assertIn('策略说明', body)
        self.assertIn('每次定投金额', body)
        self.assertIn('function validateDates', body)


if __name__ == '__main__':
    unittest.main()
