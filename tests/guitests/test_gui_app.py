import json
import os
import re
import time
import unittest
from unittest.mock import patch

from gui import web as web_module
from gui.web import app
import pandas as pd


class TestGuiRoutes(unittest.TestCase):
    def setUp(self):
        self._previous_testing = app.testing
        app.testing = True
        self.client = app.test_client()

    def tearDown(self):
        app.testing = self._previous_testing

    def _extract_task_id(self, body: str) -> str:
        match = re.search(r"const taskId = '([^']+)'", body)
        self.assertIsNotNone(match, '未找到taskId')
        return match.group(1)

    def _wait_for_task_completion(self, task_id: str, expect_error: bool = False, timeout: float = 2.0):
        deadline = time.time() + timeout
        last_status = None
        last_body = None
        while time.time() < deadline:
            resp = self.client.get(f'/api/result/{task_id}')
            last_status = resp.status_code
            last_body = resp.get_json()
            if expect_error:
                if resp.status_code == 500:
                    return last_body
            else:
                if resp.status_code == 200:
                    return last_body
            time.sleep(0.05)
        self.fail(f'回测任务未在{timeout}s内完成, status={last_status}, body={last_body}')

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

    def test_search_stock_api_supports_etf_and_fund(self):
        """测试可搜索到指数基金与场外基金。"""
        rv_etf = self.client.get('/api/search_stock?query=510300')
        self.assertEqual(rv_etf.status_code, 200)
        data_etf = rv_etf.get_json()
        self.assertEqual(data_etf.get('code'), '510300')

        rv_fund = self.client.get('/api/search_stock?query=白酒')
        self.assertEqual(rv_fund.status_code, 200)
        data_fund = rv_fund.get_json()
        self.assertEqual(data_fund.get('code'), '161725')

    @patch('stocks.create_backtest_request')
    @patch('stocks.run_backtest')
    def test_run_post_accepts_fractional_lot(self, mock_run_backtest, mock_create_request):
        """测试回测接口可接收小数交易单位。"""
        with self.client.session_transaction() as sess:
            sess['stock_code'] = '161725'
            sess['stock_name'] = '招商中证白酒指数(LOF)'

        def _fake_create_request(**kwargs):
            return kwargs

        mock_create_request.side_effect = _fake_create_request
        mock_run_backtest.return_value = {
            'symbol': '161725',
            'trades_list': [],
            'history': [],
            'total_value': 100000.0,
        }

        rv = self.client.post('/run', data={'strategy': 'fixed_amount', 'lot': '0.01', 'cash': '100000'})
        self.assertEqual(rv.status_code, 200)

        self.assertTrue(mock_create_request.called)
        kwargs = mock_create_request.call_args.kwargs
        self.assertAlmostEqual(kwargs['lot_size'], 0.01)

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
        # Now expect progress page instead of result page
        self.assertIn('回测仿真进行中', body)
        self.assertIn('600900', body)  # Stock code should be shown
        # Verify SSE connection setup is present
        self.assertIn('EventSource', body)
        task_id = self._extract_task_id(body)
        self._wait_for_task_completion(task_id)

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
        # Now expect progress page instead of result page
        body = rv.data.decode('utf-8')
        self.assertIn('回测仿真进行中', body)
        task_id = self._extract_task_id(body)
        self._wait_for_task_completion(task_id)

    def test_run_post_invalid_date_shows_error(self):
        # Set stock in session
        with self.client.session_transaction() as sess:
            sess['stock_code'] = '600900'
            sess['stock_name'] = '长江电力'

        rv = self.client.post('/run', data={'strategy': 'sma', 'start': 'invalid-date'})
        self.assertEqual(rv.status_code, 200)
        body = rv.data.decode('utf-8')
        self.assertIn('回测仿真进行中', body)
        task_id = self._extract_task_id(body)
        error_body = self._wait_for_task_completion(task_id, expect_error=True)
        self.assertIn('error', error_body)
        self.assertIn('日期格式', error_body['error'])

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

    def test_result_page_contains_stock_price_chart(self):
        """测试复盘界面包含股价波动线（使用mock数据避免污染缓存）"""
        mock_result = {
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

        rv = self.client.post('/view_result', data={'result_json': json.dumps(mock_result, ensure_ascii=False)})

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
        self.assertIn('id="time-range-chart"', body)
        self.assertIn('refresh-cache-btn', body)
        self.assertIn('function refreshChart', body)
        self.assertIn('function refreshCacheAndReload', body)
        self.assertIn('const stockCode = "600900"', body)
        self.assertIn('yesterday.setDate(yesterday.getDate() - 1)', body)

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
    def test_stock_chart_api_success(self, mock_get):
        """测试时间段页走势图数据接口"""
        with self.client.session_transaction() as sess:
            sess['stock_code'] = '600900'
            sess['stock_name'] = '长江电力'

        mock_get.return_value = pd.DataFrame({
            'date': pd.to_datetime(['2023-01-03', '2023-01-04', '2023-01-05']),
            'open': [24.1, 24.3, 24.6],
            'high': [24.5, 24.7, 24.9],
            'low': [23.9, 24.1, 24.3],
            'close': [24.2, 24.4, 24.7],
            'volume': [1000, 1200, 1300],
        })

        rv = self.client.get('/api/stock_chart/600900?start=20230103&end=20230105')
        self.assertEqual(rv.status_code, 200)
        data = rv.get_json()
        self.assertEqual(data['stock_code'], '600900')
        self.assertEqual(data['labels'], ['2023-01-03', '2023-01-04', '2023-01-05'])
        self.assertEqual(data['open_prices'], [24.1, 24.3, 24.6])
        self.assertEqual(data['price_field'], 'open')
        self.assertEqual(data['points'], 3)

    def test_stock_chart_api_requires_selected_stock(self):
        """测试未选股票时走势图接口返回错误"""
        rv = self.client.get('/api/stock_chart/600900')
        self.assertEqual(rv.status_code, 400)
        data = rv.get_json()
        self.assertIn('error', data)

    @patch('stocks.get_data')
    @patch('gui.web.os.remove')
    @patch('gui.web.os.path.isfile')
    @patch('gui.web.os.listdir')
    @patch('gui.web.os.path.isdir')
    def test_refresh_cache_api_success(self, mock_isdir, mock_listdir, mock_isfile, mock_remove, mock_get):
        """测试清除缓存并自动重下当前股票数据"""
        with self.client.session_transaction() as sess:
            sess['stock_code'] = '600900'
            sess['stock_name'] = '长江电力'

        mock_isdir.return_value = True
        mock_listdir.return_value = ['600900.csv', '000001.csv', 'README.md']
        mock_isfile.return_value = True
        mock_get.side_effect = [
            pd.DataFrame({
                'date': pd.to_datetime(['2022-12-30', '2023-01-03', '2023-01-04']),
                'open': [23.8, 24.1, 24.3],
                'high': [24.0, 24.4, 24.7],
                'low': [23.5, 23.9, 24.0],
                'close': [23.9, 24.2, 24.5],
                'volume': [900, 1000, 1100],
            }),
            pd.DataFrame({
                'date': pd.to_datetime(['2023-01-03', '2023-01-04']),
                'open': [24.1, 24.3],
                'high': [24.4, 24.7],
                'low': [23.9, 24.0],
                'close': [24.2, 24.5],
                'volume': [1000, 1100],
            }),
        ]

        rv = self.client.post(
            '/api/stock_chart/600900/refresh_cache',
            json={'start': '20230103', 'end': '20230104'},
            content_type='application/json'
        )
        self.assertEqual(rv.status_code, 200)
        data = rv.get_json()
        self.assertTrue(data['refreshed'])
        self.assertEqual(data['removed_cache_files'], 2)
        self.assertEqual(data['labels'], ['2023-01-03', '2023-01-04'])
        self.assertEqual(data['open_prices'], [24.1, 24.3])
        cache_dir = web_module._get_cache_dir()
        mock_remove.assert_any_call(os.path.join(cache_dir, '600900.csv'))
        mock_remove.assert_any_call(os.path.join(cache_dir, '000001.csv'))
        self.assertEqual(mock_get.call_count, 2)
        rebuild_call = mock_get.call_args_list[0].kwargs
        self.assertEqual(rebuild_call['start_date'], '20230103')
        self.assertEqual(rebuild_call['end_date'], '20230104')
        self.assertTrue(rebuild_call['force_refresh'])
        self.assertEqual(rebuild_call['buffer_days'], 5)

    def test_refresh_cache_api_requires_selected_stock(self):
        """测试未选股票时无法清缓存重下"""
        rv = self.client.post('/api/stock_chart/600900/refresh_cache', json={})
        self.assertEqual(rv.status_code, 400)
        data = rv.get_json()
        self.assertIn('error', data)

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
