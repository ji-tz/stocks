"""
测试 test_utils 模块
"""
import unittest
import os
import tempfile
from tests.unit.test_utils import (
    get_random_stock_code,
    get_stock_pool,
    get_cached_stock_codes,
    STOCK_POOL
)


class TestTestUtils(unittest.TestCase):
    """测试 test_utils 模块的功能"""

    def test_get_stock_pool(self):
        """测试获取股票池"""
        pool = get_stock_pool()
        self.assertIsInstance(pool, list)
        self.assertGreater(len(pool), 0)
        self.assertIn("600900", pool)  # 长江电力应该在池中

    def test_get_random_stock_code_no_seed(self):
        """测试无种子随机选择"""
        code1 = get_random_stock_code()
        self.assertIn(code1, STOCK_POOL)

        code2 = get_random_stock_code()
        self.assertIn(code2, STOCK_POOL)
        # 注意：不保证两次结果不同，只保证在股票池中

    def test_get_random_stock_code_with_seed(self):
        """测试有种子的可重现随机选择"""
        code1 = get_random_stock_code(seed=42)
        code2 = get_random_stock_code(seed=42)
        self.assertEqual(code1, code2)  # 相同种子应得到相同结果
        self.assertIn(code1, STOCK_POOL)

    def test_get_random_stock_code_with_cache_dir(self):
        """测试从缓存目录选择股票"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建一些假的缓存文件
            cache_stocks = ["600900", "600519"]
            for stock in cache_stocks:
                cache_file = os.path.join(tmpdir, f"{stock}.csv")
                with open(cache_file, 'w') as f:
                    f.write("date,open,high,low,close,volume\n")

            # 多次调用应该只返回有缓存的股票
            for _ in range(10):
                code = get_random_stock_code(cache_dir=tmpdir)
                self.assertIn(code, cache_stocks)

    def test_get_random_stock_code_fallback_no_cache(self):
        """测试无缓存时回退到完整股票池"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 空目录，无缓存文件
            code = get_random_stock_code(cache_dir=tmpdir)
            self.assertIn(code, STOCK_POOL)

    def test_get_cached_stock_codes(self):
        """测试获取有缓存的股票代码列表"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建一些假的缓存文件
            cache_stocks = ["600900", "601318"]
            for stock in cache_stocks:
                cache_file = os.path.join(tmpdir, f"{stock}.csv")
                with open(cache_file, 'w') as f:
                    f.write("date,open,high,low,close,volume\n")

            cached = get_cached_stock_codes(cache_dir=tmpdir)
            self.assertEqual(set(cached), set(cache_stocks))

    def test_get_cached_stock_codes_empty_dir(self):
        """测试空目录返回空列表"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cached = get_cached_stock_codes(cache_dir=tmpdir)
            self.assertEqual(cached, [])


if __name__ == '__main__':
    unittest.main()
