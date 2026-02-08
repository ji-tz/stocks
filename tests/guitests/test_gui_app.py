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
        # 需要先在session中设置完整流程的信息
        with self.client.session_transaction() as sess:
            sess['stock_code'] = '600900'
            sess['stock_name'] = '长江电力'
            sess['strategy_type'] = 'sma'
            sess['strategy_name'] = 'SMA'
            sess['run_mode'] = 'backtest'

        rv = self.client.get('/strategy/sma')
        self.assertEqual(rv.status_code, 200)
        body = rv.data.decode('utf-8')
        self.assertIn('第五步：配置参数', body)  # 更新为第五步
        self.assertIn('策略说明', body)
        self.assertIn('SMA 周期', body)
        self.assertIn('股票', body)
        self.assertIn('600900', body)
        self.assertIn('长江电力', body)
        # 日期验证函数已移除（时间段在上一步设置）
        self.assertNotIn('function validateDates', body)
        # 日期输入框已移除
        self.assertNotIn('起始日期', body)
        self.assertNotIn('结束日期', body)

    def test_strategy_mean_cost_get(self):
        """测试均值成本策略配置页面"""
        # 需要先在session中设置完整流程的信息
        with self.client.session_transaction() as sess:
            sess['stock_code'] = '600900'
            sess['stock_name'] = '长江电力'
            sess['strategy_type'] = 'mean_cost'
            sess['strategy_name'] = '均值成本'
            sess['run_mode'] = 'backtest'

        rv = self.client.get('/strategy/mean_cost')
        self.assertEqual(rv.status_code, 200)
        body = rv.data.decode('utf-8')
        self.assertIn('第五步：配置参数', body)  # 更新为第五步
        self.assertIn('策略说明', body)
        self.assertIn('逢低加仓', body)
        self.assertIn('股票', body)
        self.assertIn('600900', body)
        self.assertIn('长江电力', body)
        # 日期验证函数已移除
        self.assertNotIn('function validateDates', body)
        # 日期输入框已移除
        self.assertNotIn('起始日期', body)
        self.assertNotIn('结束日期', body)

    def test_strategy_fixed_amount_get(self):
        """测试定投策略配置页面"""
        # 需要先在session中设置完整流程的信息
        with self.client.session_transaction() as sess:
            sess['stock_code'] = '600900'
            sess['stock_name'] = '长江电力'
            sess['strategy_type'] = 'fixed_amount'
            sess['strategy_name'] = '定投'
            sess['run_mode'] = 'backtest'

        rv = self.client.get('/strategy/fixed_amount')
        self.assertEqual(rv.status_code, 200)
        body = rv.data.decode('utf-8')
        self.assertIn('第五步：配置参数', body)  # 更新为第五步
        self.assertIn('策略说明', body)
        self.assertIn('每次定投金额', body)
        self.assertIn('股票', body)
        self.assertIn('600900', body)
        self.assertIn('长江电力', body)
        # 日期验证函数已移除
        self.assertNotIn('function validateDates', body)
        # 日期输入框已移除
        self.assertNotIn('起始日期', body)
        self.assertNotIn('结束日期', body)

    @patch('stocks.get_data')
    @patch('stocks.run_mean_cost')
    def test_result_page_contains_stock_price_chart(self, mock_run, mock_get_data):
        """测试复盘界面包含股价波动线（使用mock数据避免污染缓存）"""
        # Mock数据以避免污染data/600900.csv
        mock_df = pd.DataFrame({
            'date': pd.date_range('2023-01-01', periods=20, freq='D'),
            'open': [22.0 + i*0.1 for i in range(20)],
            'high': [22.5 + i*0.1 for i in range(20)],
            'low': [21.5 + i*0.1 for i in range(20)],
            'close': [22.0 + i*0.1 for i in range(20)],
            'volume': [1000000 + i*10000 for i in range(20)]
        })
        mock_get_data.return_value = mock_df

        # Mock回测结果 - 包含模板需要的所有字段
        mock_run.return_value = {
            'symbol': '600900',
            'start_date': '2023-01-01',
            'end_date': '2023-01-31',
            'init_cash': 100000,
            'trades': 5,
            'shares': 100,
            'cash': 95000,
            'avg_cost': 22.5,
            'total_value': 100000,
            'realized_pl': 500,
            'unrealized_pl': 200,
            'market_value': 5000,
            'max_capital_used': 50000,
            'trades_list': [
                {'date': '2023-01-01', 'action': 'buy', 'price': 22.0, 'shares': 100, 'cash': 97800, 'shares_after': 100, 'realized_pl': 0},
                {'date': '2023-01-05', 'action': 'sell', 'price': 22.5, 'shares': 50, 'cash': 98925, 'shares_after': 50, 'realized_pl': 25},
            ],
            'history': [
                {'date': '2023-01-01', 'total_value': 100000, 'last_price': 22.0},
                {'date': '2023-01-02', 'total_value': 101000, 'last_price': 22.1},
            ]
        }

        rv = self.client.post('/run', data={
            'symbol': '600900',
            'strategy': 'mean_cost',
            'start': '20230101',
            'end': '20230131',
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

    def test_select_time_range_get(self):
        """测试回测时间段设置页面"""
        # 需要先在session中设置前三步的信息
        with self.client.session_transaction() as sess:
            sess['stock_code'] = '600900'
            sess['stock_name'] = '长江电力'
            sess['strategy_type'] = 'sma'
            sess['strategy_name'] = 'SMA策略'
            sess['run_mode'] = 'backtest'

        rv = self.client.get('/select_time_range')
        self.assertEqual(rv.status_code, 200)
        body = rv.data.decode('utf-8')
        
        # 验证页面标题和说明
        self.assertIn('第3.5步：设置回测时间段', body)
        self.assertIn('时间段设置说明', body)
        
        # 验证面包屑导航
        self.assertIn('✓ 选择股票', body)
        self.assertIn('✓ 选择策略', body)
        self.assertIn('✓ 选择运行模式', body)
        self.assertIn('设置时间段', body)
        
        # 验证已选信息显示
        self.assertIn('600900', body)
        self.assertIn('长江电力', body)
        self.assertIn('SMA策略', body)
        
        # 验证日期输入控件
        self.assertIn('<input type="date" id="start-date"', body)
        self.assertIn('<input type="date" id="end-date"', body)
        
        # 验证快捷按钮
        self.assertIn('最近1年', body)
        self.assertIn('最近2年', body)
        self.assertIn('最近3年', body)
        self.assertIn('最近5年', body)
        self.assertIn('今年至今', body)
        self.assertIn('全部数据', body)
        
        # 验证JavaScript验证函数
        self.assertIn('function validateDates', body)
        self.assertIn('function setPreset', body)

    def test_select_time_range_api_post(self):
        """测试保存回测时间段API"""
        # 需要先在session中设置前三步的信息
        with self.client.session_transaction() as sess:
            sess['stock_code'] = '600900'
            sess['stock_name'] = '长江电力'
            sess['strategy_type'] = 'sma'
            sess['strategy_name'] = 'SMA策略'
            sess['run_mode'] = 'backtest'

        # 测试保存时间段
        rv = self.client.post('/api/select_time_range',
                             json={'start': '20230101', 'end': '20231231'},
                             content_type='application/json')
        self.assertEqual(rv.status_code, 200)
        data = rv.get_json()
        self.assertTrue(data['success'])
        
        # 验证session中保存了时间段
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('backtest_start'), '20230101')
            self.assertEqual(sess.get('backtest_end'), '20231231')

    def test_select_time_range_api_post_empty_dates(self):
        """测试保存空时间段（使用全部数据）"""
        with self.client.session_transaction() as sess:
            sess['stock_code'] = '600900'
            sess['stock_name'] = '长江电力'
            sess['strategy_type'] = 'sma'
            sess['strategy_name'] = 'SMA策略'
            sess['run_mode'] = 'backtest'

        # 测试保存空时间段
        rv = self.client.post('/api/select_time_range',
                             json={'start': '', 'end': ''},
                             content_type='application/json')
        self.assertEqual(rv.status_code, 200)
        data = rv.get_json()
        self.assertTrue(data['success'])
        
        # 验证session中保存了空字符串
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('backtest_start'), '')
            self.assertEqual(sess.get('backtest_end'), '')

    @patch('stocks.get_data')
    @patch('stocks.run_sma_backtest')
    def test_run_with_session_time_range(self, mock_sma, mock_get):
        """测试/run路由从session读取时间段"""
        # 设置完整的session信息（包括时间段）
        with self.client.session_transaction() as sess:
            sess['stock_code'] = '600900'
            sess['stock_name'] = '长江电力'
            sess['backtest_start'] = '20230101'
            sess['backtest_end'] = '20231231'

        dates = pd.date_range(end="2023-12-31", periods=5, freq="D")
        df = pd.DataFrame({
            'date': dates, 'open': [100.0+i for i in range(5)], 'high': [101.0+i for i in range(5)],
            'low': [99.0+i for i in range(5)], 'close': [100.0+i for i in range(5)], 'volume': [1000+i*10 for i in range(5)]
        })
        mock_get.return_value = df
        mock_sma.return_value = {
            'symbol': '600900', 'start_date': '2023-01-01', 'end_date': '2023-12-31', 
            'init_cash': 100000.0, 'final_cash': 100500.0,
            'trades': 3, 'shares': 100, 'cash': 95000,
            'total_value': 100500, 'realized_pl': 500, 'unrealized_pl': 0,
            'history': [], 'trades_list': []
        }
        
        # 不在表单中传递时间段，应该从session读取
        rv = self.client.post('/run', data={'strategy': 'sma', 'period': '20'})
        self.assertEqual(rv.status_code, 200)
        
        # 验证调用时使用了session中的时间段
        mock_sma.assert_called_once()
        call_args = mock_sma.call_args
        self.assertEqual(call_args[1]['start_date'], '20230101')
        self.assertEqual(call_args[1]['end_date'], '20231231')
