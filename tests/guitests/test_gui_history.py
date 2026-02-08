"""测试历史记录和对比功能的GUI路由"""
import json
import re
import time
import unittest
from unittest.mock import patch, MagicMock

from gui.web import app
import backtest_records


class TestHistoryAndCompareRoutes(unittest.TestCase):
    """测试历史记录和对比功能的路由"""

    def setUp(self):
        """测试前准备"""
        self.client = app.test_client()
        # 清空测试前的记录
        backtest_records.clear_all()

    def _extract_task_id(self, body: str) -> str:
        match = re.search(r"const taskId = '([^']+)'", body)
        self.assertIsNotNone(match, '未找到taskId')
        return match.group(1)

    def _wait_for_task_completion(self, task_id: str, timeout: float = 2.0):
        deadline = time.time() + timeout
        last_status = None
        last_body = None
        while time.time() < deadline:
            resp = self.client.get(f'/api/result/{task_id}')
            last_status = resp.status_code
            last_body = resp.get_json()
            if resp.status_code in (200, 500):
                return last_body
            time.sleep(0.05)
        self.fail(f'回测任务未在{timeout}s内完成, status={last_status}, body={last_body}')

    def tearDown(self):
        """测试后清理"""
        # 清空测试后的记录
        backtest_records.clear_all()

    def test_history_page_empty(self):
        """测试空历史记录页面"""
        response = self.client.get('/history')
        self.assertEqual(response.status_code, 200)
        body = response.data.decode('utf-8')
        self.assertIn('回测历史记录', body)
        self.assertIn('暂无回测记录', body)

    def test_history_page_with_records(self):
        """测试包含记录的历史页面"""
        # 添加测试记录
        backtest_records.add_record(
            strategy='sma',
            symbol='600900',
            parameters={'period': 20, 'cash': 100000},
            result={'init_cash': 100000, 'total_value': 110000, 'trades': 10,
                   'shares': 1000, 'cash': 10000, 'realized_pl': 5000,
                   'unrealized_pl': 5000, 'start_date': '2025-01-01',
                   'end_date': '2025-01-31'}
        )

        response = self.client.get('/history')
        self.assertEqual(response.status_code, 200)
        body = response.data.decode('utf-8')
        self.assertIn('回测历史记录', body)
        self.assertIn('600900', body)
        self.assertIn('SMA策略', body)
        self.assertNotIn('暂无回测记录', body)

    def test_compare_page_empty(self):
        """测试空对比页面"""
        response = self.client.get('/compare')
        self.assertEqual(response.status_code, 200)
        body = response.data.decode('utf-8')
        self.assertIn('回测记录对比', body)
        self.assertIn('请选择至少2条记录进行对比', body)

    def test_compare_page_with_records(self):
        """测试对比页面（包含记录）"""
        # 添加两条测试记录
        id1 = backtest_records.add_record(
            strategy='sma',
            symbol='600900',
            parameters={'period': 20, 'cash': 100000},
            result={'init_cash': 100000, 'total_value': 110000, 'trades': 10,
                   'shares': 1000, 'cash': 10000, 'realized_pl': 5000,
                   'unrealized_pl': 5000, 'start_date': '2025-01-01',
                   'end_date': '2025-01-31', 'history': []}
        )

        id2 = backtest_records.add_record(
            strategy='mean_cost',
            symbol='600519',
            parameters={'cash': 100000},
            result={'init_cash': 100000, 'total_value': 105000, 'trades': 15,
                   'shares': 500, 'cash': 5000, 'realized_pl': 3000,
                   'unrealized_pl': 2000, 'start_date': '2025-01-01',
                   'end_date': '2025-01-31', 'history': []}
        )

        response = self.client.get(f'/compare?ids={id1}&ids={id2}')
        self.assertEqual(response.status_code, 200)
        body = response.data.decode('utf-8')
        self.assertIn('回测记录对比', body)
        self.assertIn('600900', body)
        self.assertIn('600519', body)
        self.assertIn('SMA策略', body)
        self.assertIn('均值成本', body)

    def test_api_records_empty(self):
        """测试获取空记录列表API"""
        response = self.client.get('/api/records')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('records', data)
        self.assertEqual(len(data['records']), 0)

    def test_api_records_with_data(self):
        """测试获取记录列表API"""
        # 添加测试记录
        backtest_records.add_record(
            strategy='sma',
            symbol='600900',
            parameters={'period': 20},
            result={'init_cash': 100000, 'total_value': 110000, 'trades': 10,
                   'shares': 1000, 'cash': 10000, 'realized_pl': 5000,
                   'unrealized_pl': 5000}
        )

        response = self.client.get('/api/records')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('records', data)
        self.assertEqual(len(data['records']), 1)
        self.assertEqual(data['records'][0]['symbol'], '600900')

    def test_api_get_record(self):
        """测试获取单条记录API"""
        # 添加测试记录
        record_id = backtest_records.add_record(
            strategy='fixed_amount',
            symbol='000001',
            parameters={'fixed_amount': 1000},
            result={'init_cash': 100000, 'total_value': 120000, 'trades': 20,
                   'shares': 2000, 'cash': 20000, 'realized_pl': 10000,
                   'unrealized_pl': 10000}
        )

        response = self.client.get(f'/api/record/{record_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['id'], record_id)
        self.assertEqual(data['symbol'], '000001')
        self.assertEqual(data['strategy'], 'fixed_amount')

    def test_api_get_nonexistent_record(self):
        """测试获取不存在的记录"""
        response = self.client.get('/api/record/nonexistent')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_api_delete_record(self):
        """测试删除记录API"""
        # 添加测试记录
        record_id = backtest_records.add_record(
            strategy='sma',
            symbol='600900',
            parameters={'period': 20},
            result={'init_cash': 100000, 'total_value': 110000, 'trades': 10,
                   'shares': 1000, 'cash': 10000, 'realized_pl': 5000,
                   'unrealized_pl': 5000}
        )

        # 验证记录存在
        self.assertIsNotNone(backtest_records.get_record(record_id))

        # 删除记录
        response = self.client.delete(f'/api/record/{record_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])

        # 验证记录已删除
        self.assertIsNone(backtest_records.get_record(record_id))

    def test_api_delete_nonexistent_record(self):
        """测试删除不存在的记录"""
        response = self.client.delete('/api/record/nonexistent')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertFalse(data['success'])

    @patch('stocks.run_mean_cost')
    @patch('stocks.get_data')
    def test_run_saves_record(self, mock_get_data, mock_run_mean_cost):
        """测试运行回测时自动保存记录"""
        import pandas as pd

        # Mock数据
        dates = pd.date_range(end="2025-01-31", periods=5, freq="D")
        mock_get_data.return_value = pd.DataFrame({
            'date': dates,
            'open': [100.0] * 5,
            'high': [101.0] * 5,
            'low': [99.0] * 5,
            'close': [100.0] * 5,
            'volume': [1000] * 5
        })

        mock_run_mean_cost.return_value = {
            'symbol': '600900',
            'start_date': '2025-01-01',
            'end_date': '2025-01-31',
            'init_cash': 50000.0,
            'total_value': 55000.0,
            'trades': 5,
            'shares': 500,
            'cash': 5000,
            'realized_pl': 2500,
            'unrealized_pl': 2500,
            'history': [],
            'trades_list': []
        }

        # 清空记录
        backtest_records.clear_all()

        # 运行回测
        response = self.client.post('/run', data={
            'symbol': '600900',
            'strategy': 'mean_cost',
            'start': '20250101',
            'end': '20250131',
            'cash': '50000'
        })

        self.assertEqual(response.status_code, 200)
        task_id = self._extract_task_id(response.data.decode('utf-8'))
        self._wait_for_task_completion(task_id)

        # 验证记录已保存
        records = backtest_records.get_records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['symbol'], '600900')
        self.assertEqual(records[0]['strategy'], 'mean_cost')


if __name__ == '__main__':
    unittest.main()
