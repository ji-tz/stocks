"""测试策略参数配置界面的实时计算功能

测试每手金额和资金支持手数的实时计算显示功能。
"""
import unittest
from unittest.mock import patch
import pandas as pd
from gui.web import app


class TestRealtimeLotCalculation(unittest.TestCase):
    """测试策略参数配置界面的实时计算功能"""

    def setUp(self):
        """设置测试客户端"""
        self.client = app.test_client()

    def test_stock_price_api_success(self):
        """测试获取股票价格API - 成功场景"""
        # Mock get_data 返回测试数据
        test_data = pd.DataFrame({
            'date': pd.date_range(end='2024-01-10', periods=5),
            'open': [10.0, 10.5, 11.0, 10.8, 11.2],
            'high': [10.5, 11.0, 11.5, 11.2, 11.8],
            'low': [9.5, 10.0, 10.5, 10.3, 10.9],
            'close': [10.0, 10.5, 11.0, 10.8, 11.5],
            'volume': [1000, 1100, 1200, 1150, 1300]
        })

        with patch('stocks.get_data', return_value=test_data):
            response = self.client.get('/api/stock_price/600900')
            self.assertEqual(response.status_code, 200)

            data = response.get_json()
            self.assertIn('price', data)
            self.assertIn('date', data)
            self.assertIn('stock_code', data)

            # 验证返回的是最新价格（最后一天的收盘价）
            self.assertEqual(data['price'], 11.5)
            self.assertEqual(data['stock_code'], '600900')
            self.assertIn('2024-01-10', data['date'])

    @patch('stocks.get_data')
    def test_stock_price_api_uses_project_cache_dir(self, mock_get_data):
        """测试获取价格接口使用项目绝对缓存目录"""
        test_data = pd.DataFrame({
            'date': pd.to_datetime(['2024-01-10']),
            'open': [10.0],
            'high': [10.5],
            'low': [9.5],
            'close': [10.0],
            'volume': [1000]
        })
        mock_get_data.return_value = test_data

        response = self.client.get('/api/stock_price/600900')
        self.assertEqual(response.status_code, 200)

        from gui.web import _get_cache_dir
        self.assertEqual(mock_get_data.call_args.kwargs.get('cache_dir'), _get_cache_dir())

    def test_stock_price_api_empty_data(self):
        """测试获取股票价格API - 空数据场景"""
        # Mock get_data 返回空DataFrame
        empty_df = pd.DataFrame()

        with patch('stocks.get_data', return_value=empty_df):
            response = self.client.get('/api/stock_price/600900')
            self.assertEqual(response.status_code, 404)

            data = response.get_json()
            self.assertIn('error', data)
            self.assertIn('无法获取股票数据', data['error'])

    def test_stock_price_api_exception(self):
        """测试获取股票价格API - 异常场景"""
        # Mock get_data 抛出异常
        with patch('stocks.get_data', side_effect=Exception('网络错误')):
            response = self.client.get('/api/stock_price/600900')
            self.assertEqual(response.status_code, 500)

            data = response.get_json()
            self.assertIn('error', data)
            self.assertIn('获取价格失败', data['error'])

    def test_strategy_sma_page_contains_realtime_info(self):
        """测试SMA策略页面包含实时计算区域"""
        # 设置session
        with self.client.session_transaction() as sess:
            sess['stock_code'] = '600900'
            sess['stock_name'] = '长江电力'
            sess['strategy_type'] = 'sma'
            sess['run_mode'] = 'backtest'

        response = self.client.get('/strategy/sma')
        self.assertEqual(response.status_code, 200)

        html = response.data.decode('utf-8')
        # 验证实时计算区域存在
        self.assertIn('id="realtime-info"', html)
        self.assertIn('id="lot-amount"', html)
        self.assertIn('id="affordable-lots"', html)
        self.assertIn('id="price-info"', html)

        # 验证JavaScript实时计算逻辑存在
        self.assertIn('fetchStockPrice', html)
        self.assertIn('updateCalculations', html)
        self.assertIn('encodeURIComponent', html)

        # 验证XSS防护：stock_code使用了tojson过滤器
        self.assertIn('const stockCode =', html)
        # 确保使用了JSON序列化而不是直接插入
        self.assertIn('"600900"', html)

    def test_strategy_mean_cost_page_contains_realtime_info(self):
        """测试均值成本策略页面包含实时计算区域"""
        # 设置session
        with self.client.session_transaction() as sess:
            sess['stock_code'] = '600519'
            sess['stock_name'] = '贵州茅台'
            sess['strategy_type'] = 'mean_cost'
            sess['run_mode'] = 'backtest'

        response = self.client.get('/strategy/mean_cost')
        self.assertEqual(response.status_code, 200)

        html = response.data.decode('utf-8')
        # 验证实时计算区域存在
        self.assertIn('id="realtime-info"', html)
        self.assertIn('id="lot-amount"', html)
        self.assertIn('id="affordable-lots"', html)

        # 验证JavaScript实时计算逻辑存在
        self.assertIn('fetchStockPrice', html)
        self.assertIn('updateCalculations', html)

        # 验证XSS防护
        self.assertIn('"600519"', html)

    def test_strategy_fixed_amount_page_contains_realtime_info(self):
        """测试定投策略页面包含实时计算区域"""
        # 设置session
        with self.client.session_transaction() as sess:
            sess['stock_code'] = '000001'
            sess['stock_name'] = '平安银行'
            sess['strategy_type'] = 'fixed_amount'
            sess['run_mode'] = 'backtest'

        response = self.client.get('/strategy/fixed_amount')
        self.assertEqual(response.status_code, 200)

        html = response.data.decode('utf-8')
        # 验证实时计算区域存在
        self.assertIn('id="realtime-info"', html)
        self.assertIn('id="fixed-amount"', html)
        self.assertIn('id="lot-amount"', html)
        self.assertIn('id="fixed-amount-multiple"', html)
        self.assertIn('id="affordable-lots"', html)
        self.assertIn('定投金额是一手金额的整数倍', html)

        # 验证JavaScript实时计算逻辑存在
        self.assertIn('fetchStockPrice', html)
        self.assertIn('updateCalculations', html)
        self.assertIn('Math.floor(fixedAmount / lotAmount)', html)
        self.assertIn("fixedAmountMultipleSpan.classList.add('warning-text')", html)

        # 验证XSS防护
        self.assertIn('"000001"', html)

    def test_xss_protection_in_stock_code(self):
        """测试XSS防护：确保stock_code被正确转义"""
        # 设置一个可能包含XSS攻击的股票代码（虽然实际不会这样，但测试防护机制）
        with self.client.session_transaction() as sess:
            sess['stock_code'] = '600900'  # 正常代码
            sess['stock_name'] = '长江电力'
            sess['strategy_type'] = 'sma'
            sess['run_mode'] = 'backtest'

        response = self.client.get('/strategy/sma')
        self.assertEqual(response.status_code, 200)

        html = response.data.decode('utf-8')
        # 确保使用了JSON序列化（tojson过滤器）
        # stockCode应该被正确序列化为JSON字符串
        self.assertIn('const stockCode = "600900"', html)
        # 确保URL拼接使用了encodeURIComponent
        self.assertIn('encodeURIComponent(stockCode)', html)


if __name__ == '__main__':
    unittest.main()
