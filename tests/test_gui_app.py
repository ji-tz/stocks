import unittest
from unittest.mock import patch

from gui.web import app
import pandas as pd


class TestGuiRoutes(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_index_get(self):
        """测试股票选择首页"""
        rv = self.client.get('/')
        self.assertEqual(rv.status_code, 200)
        # page title should be present (Chinese)
        body = rv.data.decode('utf-8')
        self.assertIn('量化回测平台', body)
        self.assertIn('第一步：选择股票', body)
        # ensure stock search box is present
        self.assertIn('搜索股票', body)
        self.assertIn('热门股票', body)
        # ensure popular stocks are displayed
        self.assertIn('600900', body)
        self.assertIn('长江电力', body)
        self.assertIn('600519', body)
        self.assertIn('贵州茅台', body)

    @patch('stocks.get_data')
    @patch('stocks.run_mean_cost')
    def test_run_mean_cost_post(self, mock_mean, mock_get):
        # Set stock in session
        with self.client.session_transaction() as sess:
            sess['stock_code'] = '600900'
            sess['stock_name'] = '长江电力'
        
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
        rv = self.client.post('/run', data={'strategy': 'mean_cost', 'start': '20230101', 'end': '20231231'})
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
        # Set stock in session
        with self.client.session_transaction() as sess:
            sess['stock_code'] = '600900'
            sess['stock_name'] = '长江电力'
        
        dates = pd.date_range(end="2023-12-31", periods=5, freq="D")
        df = pd.DataFrame({
            'date': dates, 'open': [100.0+i for i in range(5)], 'high': [101.0+i for i in range(5)],
            'low': [99.0+i for i in range(5)], 'close': [100.0+i for i in range(5)], 'volume': [1000+i*10 for i in range(5)]
        })
        mock_get.return_value = df
        mock_sma.return_value = {'symbol': '600900', 'start_date': '2023-01-01', 'end_date': '2023-01-10', 'init_cash': 100000.0, 'final_cash': 100500.0}
        rv = self.client.post('/run', data={'strategy': 'sma', 'start': '20230101', 'end': '20231231'})
        self.assertEqual(rv.status_code, 200)
        self.assertIn('回测结果', rv.data.decode('utf-8'))
        mock_get.assert_called()

    def test_run_post_invalid_date_shows_error(self):
        # Set stock in session
        with self.client.session_transaction() as sess:
            sess['stock_code'] = '600900'
            sess['stock_name'] = '长江电力'
        
        rv = self.client.post('/run', data={'strategy': 'sma', 'start': 'invalid-date'})
        self.assertEqual(rv.status_code, 200)
        self.assertIn('发生错误', rv.data.decode('utf-8'))

    def test_strategy_sma_get(self):
        """测试 SMA 策略配置页面"""
        # 需要先在session中设置股票信息
        with self.client.session_transaction() as sess:
            sess['stock_code'] = '600900'
            sess['stock_name'] = '长江电力'
        
        rv = self.client.get('/strategy/sma')
        self.assertEqual(rv.status_code, 200)
        body = rv.data.decode('utf-8')
        self.assertIn('SMA 策略回测', body)
        self.assertIn('策略说明', body)
        self.assertIn('SMA 周期', body)
        self.assertIn('已选择股票', body)
        self.assertIn('600900', body)
        self.assertIn('长江电力', body)
        self.assertIn('function validateDates', body)

    def test_strategy_mean_cost_get(self):
        """测试均值成本策略配置页面"""
        # 需要先在session中设置股票信息
        with self.client.session_transaction() as sess:
            sess['stock_code'] = '600900'
            sess['stock_name'] = '长江电力'
        
        rv = self.client.get('/strategy/mean_cost')
        self.assertEqual(rv.status_code, 200)
        body = rv.data.decode('utf-8')
        self.assertIn('均值成本策略回测', body)
        self.assertIn('策略说明', body)
        self.assertIn('逢低加仓', body)
        self.assertIn('已选择股票', body)
        self.assertIn('600900', body)
        self.assertIn('长江电力', body)
        self.assertIn('function validateDates', body)

    def test_strategy_fixed_amount_get(self):
        """测试定投策略配置页面"""
        # 需要先在session中设置股票信息
        with self.client.session_transaction() as sess:
            sess['stock_code'] = '600900'
            sess['stock_name'] = '长江电力'
        
        rv = self.client.get('/strategy/fixed_amount')
        self.assertEqual(rv.status_code, 200)
        body = rv.data.decode('utf-8')
        self.assertIn('定投策略回测', body)
        self.assertIn('策略说明', body)
        self.assertIn('每次定投金额', body)
        self.assertIn('已选择股票', body)
        self.assertIn('600900', body)
        self.assertIn('长江电力', body)
        self.assertIn('function validateDates', body)

    def test_result_page_contains_stock_price_chart(self):
        """测试复盘界面包含股价波动线（使用长江电力真实数据）"""
        # 使用真实的长江电力数据进行测试
        rv = self.client.post('/run', data={
            'symbol': '600900',  # 长江电力
            'strategy': 'mean_cost',
            'start': '20230101',
            'end': '20230131',  # 使用一个月的数据
            'cash': '100000'
        })
        
        self.assertEqual(rv.status_code, 200)
        body = rv.data.decode('utf-8')
        
        # 验证页面包含图表元素
        self.assertIn('<canvas id="chart"', body)
        
        # 验证包含总资产数据数组
        self.assertIn('totalValueData', body)
        
        # 验证包含股价数据数组
        self.assertIn('stockPriceData', body)
        
        # 验证包含归一化数据数组
        self.assertIn('normalizedTotalValue', body)
        self.assertIn('normalizedStockPrice', body)
        
        # 验证两条曲线使用同一个Y轴
        self.assertIn("yAxisID: 'y'", body)
        
        # 验证已移除双Y轴配置
        self.assertNotIn("yAxisID: 'y1'", body)
        
        # 验证包含图表标签
        self.assertIn('总资产变化', body)
        self.assertIn('股价变化', body)
        
        # 验证Y轴标题显示相对变化
        self.assertIn('相对变化（起点=100）', body)
        
        # 验证股票代码显示正确
        self.assertIn('600900', body)
    def test_api_search_stock_by_code(self):
        """测试通过股票代码搜索API"""
        rv = self.client.get('/api/search_stock?query=600900')
        self.assertEqual(rv.status_code, 200)
        data = rv.get_json()
        self.assertEqual(data['code'], '600900')
        self.assertEqual(data['name'], '长江电力')

    def test_api_search_stock_by_name(self):
        """测试通过股票名称搜索API"""
        rv = self.client.get('/api/search_stock?query=贵州茅台')
        self.assertEqual(rv.status_code, 200)
        data = rv.get_json()
        self.assertEqual(data['code'], '600519')
        self.assertEqual(data['name'], '贵州茅台')

    def test_api_search_stock_not_found(self):
        """测试搜索不存在的股票"""
        rv = self.client.get('/api/search_stock?query=不存在的股票')
        self.assertEqual(rv.status_code, 200)
        data = rv.get_json()
        self.assertIn('error', data)

    def test_api_select_stock(self):
        """测试选择股票API"""
        rv = self.client.post('/api/select_stock',
                             json={'code': '600519', 'name': '贵州茅台'},
                             content_type='application/json')
        self.assertEqual(rv.status_code, 200)
        data = rv.get_json()
        self.assertTrue(data['success'])

    def test_select_strategy_get(self):
        """测试策略选择页面"""
        # 需要先在session中设置股票信息
        with self.client.session_transaction() as sess:
            sess['stock_code'] = '600519'
            sess['stock_name'] = '贵州茅台'
        
        rv = self.client.get('/select_strategy')
        self.assertEqual(rv.status_code, 200)
        body = rv.data.decode('utf-8')
        self.assertIn('第二步：选择策略', body)
        self.assertIn('已选择股票', body)
        self.assertIn('600519', body)
        self.assertIn('贵州茅台', body)
        self.assertIn('SMA 策略', body)
        self.assertIn('均值成本策略', body)
        self.assertIn('定投策略', body)

    def test_strategy_without_stock_redirects(self):
        """测试未选择股票时访问策略页面应返回股票选择页"""
        rv = self.client.get('/strategy/sma')
        self.assertEqual(rv.status_code, 200)
        body = rv.data.decode('utf-8')
        # Should show stock selection page
        self.assertIn('第一步：选择股票', body)
        self.assertIn('搜索股票', body)


if __name__ == '__main__':
    unittest.main()
