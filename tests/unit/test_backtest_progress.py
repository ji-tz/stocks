"""测试回测进度功能

验证进度条在回测过程中的功能
"""
import unittest
from gui.backtest_progress import BacktestProgress


class TestBacktestProgress(unittest.TestCase):
    """测试回测进度管理器"""

    def setUp(self):
        """设置测试环境"""
        self.progress = BacktestProgress()

    def test_create_task(self):
        """测试创建任务"""
        task_id = self.progress.create_task()
        self.assertIsNotNone(task_id)

        task = self.progress.get_task(task_id)
        self.assertIsNotNone(task)
        self.assertEqual(task['status'], 'pending')
        self.assertEqual(task['progress'], 0)
        self.assertEqual(task['total'], 0)

    def test_update_progress(self):
        """测试更新进度"""
        task_id = self.progress.create_task()

        # 更新进度
        self.progress.update_progress(task_id, 50, 100)

        task = self.progress.get_task(task_id)
        self.assertEqual(task['status'], 'running')
        self.assertEqual(task['progress'], 50)
        self.assertEqual(task['total'], 100)

    def test_set_result(self):
        """测试设置结果"""
        task_id = self.progress.create_task()

        result = {'final_value': 120000.0, 'profit': 20000.0}
        self.progress.set_result(task_id, result)

        task = self.progress.get_task(task_id)
        self.assertEqual(task['status'], 'completed')
        self.assertEqual(task['result'], result)

    def test_set_error(self):
        """测试设置错误"""
        task_id = self.progress.create_task()

        error_msg = '数据获取失败'
        self.progress.set_error(task_id, error_msg)

        task = self.progress.get_task(task_id)
        self.assertEqual(task['status'], 'error')
        self.assertEqual(task['error'], error_msg)

    def test_get_events(self):
        """测试事件流"""
        task_id = self.progress.create_task()

        # 在另一个线程中更新进度
        import threading
        import time

        def update_progress():
            time.sleep(0.1)
            self.progress.update_progress(task_id, 25, 100)
            time.sleep(0.1)
            self.progress.update_progress(task_id, 50, 100)
            time.sleep(0.1)
            self.progress.update_progress(task_id, 75, 100)
            time.sleep(0.1)
            self.progress.set_result(task_id, {'success': True})

        thread = threading.Thread(target=update_progress)
        thread.start()

        # 收集事件
        events = []
        for event in self.progress.get_events(task_id):
            events.append(event)

        thread.join()

        # 验证事件
        self.assertEqual(len(events), 4)  # 3个进度更新 + 1个完成事件
        self.assertEqual(events[0]['type'], 'progress')
        self.assertEqual(events[0]['percentage'], 25)
        self.assertEqual(events[-1]['type'], 'completed')

    def test_cleanup_task(self):
        """测试清理任务"""
        task_id = self.progress.create_task()

        # 任务应该存在
        self.assertIsNotNone(self.progress.get_task(task_id))

        # 清理任务
        self.progress.cleanup_task(task_id)

        # 任务应该不存在了
        self.assertIsNone(self.progress.get_task(task_id))

    def test_cancel_task(self):
        """测试取消任务会推送取消事件。"""
        task_id = self.progress.create_task()

        self.progress.cancel_task(task_id)

        task = self.progress.get_task(task_id)
        self.assertIsNotNone(task)
        self.assertEqual(task['status'], 'cancelled')
        self.assertTrue(self.progress.is_cancelled(task_id))

        events = list(self.progress.get_events(task_id))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['type'], 'cancelled')


class TestSimulatorProgressCallback(unittest.TestCase):
    """测试模拟器进度回调"""

    def test_progress_callback_in_simulator(self):
        """测试模拟器中的进度回调（tick-by-tick 结构化 tick_data）"""
        from trader.simulator import Simulator
        from strategy.mean_cost_strategy import MeanCostDecision
        import pandas as pd
        from datetime import datetime, timedelta

        # 创建测试数据
        start_date = datetime(2023, 1, 1)
        dates = [start_date + timedelta(days=i) for i in range(50)]
        df = pd.DataFrame({
            'date': dates,
            'open': [10.0 + i * 0.1 for i in range(50)],
            'high': [10.5 + i * 0.1 for i in range(50)],
            'low': [9.5 + i * 0.1 for i in range(50)],
            'close': [10.0 + i * 0.1 for i in range(50)],
            'volume': [1000000] * 50
        })

        # 记录 tick_data 回调
        tick_calls = []

        def progress_callback(tick_data):
            tick_calls.append(tick_data)

        # 运行模拟（禁用 pacing 加速测试）
        sim = Simulator(lot_size=100, init_cash=100000.0)
        strategy = MeanCostDecision()
        result = sim.simulate(df=df, strategy=strategy, symbol='TEST',
                              progress_callback=progress_callback,
                              tick_interval=0.0)

        # 验证 tick_data 回调
        self.assertGreater(len(tick_calls), 0)

        # 验证第一个 tick 结构
        first_tick = tick_calls[0]
        self.assertEqual(first_tick["type"], "tick")
        self.assertIn("date", first_tick)
        self.assertIn("close_price", first_tick)
        self.assertIn("open_price", first_tick)
        self.assertIn("position", first_tick)
        self.assertIn("account", first_tick)
        self.assertIn("progress", first_tick)
        self.assertEqual(first_tick["progress"]["total"], 50)
        self.assertEqual(first_tick["progress"]["current"], 1)

        # 验证最后一个 tick
        last_tick = tick_calls[-1]
        self.assertEqual(last_tick["progress"]["current"], 50)
        self.assertEqual(last_tick["progress"]["total"], 50)

        # 验证结果
        self.assertIsNotNone(result)
        self.assertIn('total_value', result)


if __name__ == '__main__':
    unittest.main()
