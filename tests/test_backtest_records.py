"""回测记录管理模块的单元测试"""
import os
import unittest
import tempfile
import shutil
from backtest_records import BacktestRecords


class TestBacktestRecords(unittest.TestCase):
    """测试回测记录管理功能"""
    
    def setUp(self):
        """测试前准备：创建临时目录"""
        self.test_dir = tempfile.mkdtemp()
        self.storage_file = os.path.join(self.test_dir, 'test_records.json')
        self.manager = BacktestRecords(storage_file=self.storage_file, max_records=5)
    
    def tearDown(self):
        """测试后清理：删除临时目录"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_add_record(self):
        """测试添加记录"""
        record_id = self.manager.add_record(
            strategy='sma',
            symbol='600900',
            parameters={'period': 20, 'cash': 100000},
            result={'total_value': 120000, 'trades': 10}
        )
        
        self.assertIsNotNone(record_id)
        self.assertTrue(len(record_id) > 0)
        
        # 验证记录已保存
        records = self.manager.get_records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['id'], record_id)
        self.assertEqual(records[0]['strategy'], 'sma')
        self.assertEqual(records[0]['symbol'], '600900')
    
    def test_get_records(self):
        """测试获取记录列表"""
        # 添加3条记录
        id1 = self.manager.add_record('sma', '600900', {}, {'total_value': 100000})
        id2 = self.manager.add_record('mean_cost', '600519', {}, {'total_value': 110000})
        id3 = self.manager.add_record('fixed_amount', '000001', {}, {'total_value': 120000})
        
        records = self.manager.get_records()
        self.assertEqual(len(records), 3)
        
        # 验证记录顺序（最新的在前）
        self.assertEqual(records[0]['id'], id3)
        self.assertEqual(records[1]['id'], id2)
        self.assertEqual(records[2]['id'], id1)
    
    def test_get_records_with_limit(self):
        """测试限制返回记录数量"""
        # 添加5条记录
        for i in range(5):
            self.manager.add_record('sma', f'60090{i}', {}, {'total_value': 100000 + i * 1000})
        
        # 限制返回3条
        records = self.manager.get_records(limit=3)
        self.assertEqual(len(records), 3)
    
    def test_max_records_limit(self):
        """测试最大记录数限制（FIFO）"""
        # 添加6条记录（超过最大值5）
        ids = []
        for i in range(6):
            record_id = self.manager.add_record('sma', f'60090{i}', {}, {'total_value': 100000 + i * 1000})
            ids.append(record_id)
        
        records = self.manager.get_records()
        
        # 应该只保留最新的5条
        self.assertEqual(len(records), 5)
        
        # 最旧的记录（ids[0]）应该被删除
        self.assertNotIn(ids[0], [r['id'] for r in records])
        
        # 最新的5条记录应该存在
        for i in range(1, 6):
            self.assertIn(ids[i], [r['id'] for r in records])
    
    def test_get_record(self):
        """测试获取单条记录"""
        record_id = self.manager.add_record(
            strategy='mean_cost',
            symbol='600519',
            parameters={'lot': 100, 'cash': 50000},
            result={'total_value': 55000, 'trades': 20}
        )
        
        record = self.manager.get_record(record_id)
        self.assertIsNotNone(record)
        self.assertEqual(record['id'], record_id)
        self.assertEqual(record['strategy'], 'mean_cost')
        self.assertEqual(record['symbol'], '600519')
        self.assertEqual(record['parameters']['lot'], 100)
        self.assertEqual(record['result']['total_value'], 55000)
    
    def test_get_nonexistent_record(self):
        """测试获取不存在的记录"""
        record = self.manager.get_record('nonexistent_id')
        self.assertIsNone(record)
    
    def test_delete_record(self):
        """测试删除记录"""
        # 添加3条记录
        id1 = self.manager.add_record('sma', '600900', {}, {'total_value': 100000})
        id2 = self.manager.add_record('mean_cost', '600519', {}, {'total_value': 110000})
        id3 = self.manager.add_record('fixed_amount', '000001', {}, {'total_value': 120000})
        
        # 删除第2条
        success = self.manager.delete_record(id2)
        self.assertTrue(success)
        
        # 验证记录已删除
        records = self.manager.get_records()
        self.assertEqual(len(records), 2)
        self.assertNotIn(id2, [r['id'] for r in records])
        self.assertIn(id1, [r['id'] for r in records])
        self.assertIn(id3, [r['id'] for r in records])
    
    def test_delete_nonexistent_record(self):
        """测试删除不存在的记录"""
        success = self.manager.delete_record('nonexistent_id')
        self.assertFalse(success)
    
    def test_clear_all(self):
        """测试清空所有记录"""
        # 添加几条记录
        for i in range(3):
            self.manager.add_record('sma', f'60090{i}', {}, {'total_value': 100000})
        
        # 验证记录存在
        self.assertEqual(len(self.manager.get_records()), 3)
        
        # 清空
        self.manager.clear_all()
        
        # 验证已清空
        self.assertEqual(len(self.manager.get_records()), 0)
    
    def test_persistence(self):
        """测试数据持久化"""
        # 添加记录
        record_id = self.manager.add_record('sma', '600900', {}, {'total_value': 100000})
        
        # 创建新的管理器实例（模拟重启）
        new_manager = BacktestRecords(storage_file=self.storage_file, max_records=5)
        
        # 验证记录仍然存在
        records = new_manager.get_records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['id'], record_id)
    
    def test_empty_storage(self):
        """测试空存储文件"""
        # 不添加任何记录，直接读取
        records = self.manager.get_records()
        self.assertEqual(len(records), 0)


if __name__ == '__main__':
    unittest.main()
