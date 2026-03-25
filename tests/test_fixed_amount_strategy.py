"""
测试定投策略（Fixed Amount Investment Strategy）
"""
import unittest
from unittest.mock import patch
import pandas as pd
import datetime

from simulator.simulator import Simulator, simulate_fixed_amount
from solver.fixed_amount_strategy import FixedAmountDecision


def make_test_df(n=10, start_price=100.0):
    """生成测试用的价格数据"""
    dates = pd.date_range(end="2023-12-31", periods=n, freq="D")
    data = {
        "date": dates,
        "open": [start_price + i for i in range(n)],
        "high": [start_price + i + 1 for i in range(n)],
        "low": [start_price + i - 1 for i in range(n)],
        "close": [start_price + i for i in range(n)],
        "volume": [1000 + i * 10 for i in range(n)],
    }
    return pd.DataFrame(data)


class TestFixedAmountDecision(unittest.TestCase):
    """测试定投策略决策逻辑"""
    
    def test_always_buy(self):
        """测试定投策略总是返回买入"""
        strategy = FixedAmountDecision(fixed_amount=1000.0)
        
        # 无论什么情况都应该返回 'buy'
        action = strategy.decide(open_price=100.0, shares=0)
        self.assertEqual(action, 'buy')
        
        action = strategy.decide(open_price=100.0, shares=100)
        self.assertEqual(action, 'buy')
        
        action = strategy.decide(open_price=50.0, shares=1000)
        self.assertEqual(action, 'buy')
    
    def test_calculate_shares_basic(self):
        """测试股数计算：基本场景"""
        strategy = FixedAmountDecision(fixed_amount=1000.0)
        
        # 价格 100，固定金额 1000，应该买 10 股（向下取整到 0 个 lot）
        shares = strategy.calculate_shares(price=100.0, lot_size=100)
        self.assertEqual(shares, 0)  # 10股不足1手（100股）
        
        # 价格 10，固定金额 1000，应该买 100 股（1 个 lot）
        shares = strategy.calculate_shares(price=10.0, lot_size=100)
        self.assertEqual(shares, 100)
        
        # 价格 5，固定金额 1000，应该买 200 股（2 个 lot）
        shares = strategy.calculate_shares(price=5.0, lot_size=100)
        self.assertEqual(shares, 200)
    
    def test_calculate_shares_rounding(self):
        """测试股数计算：向下取整"""
        strategy = FixedAmountDecision(fixed_amount=1000.0)
        
        # 价格 7，固定金额 1000，应该买 142 股 -> 向下取整到 100 股
        shares = strategy.calculate_shares(price=7.0, lot_size=100)
        self.assertEqual(shares, 100)
        
        # 价格 3，固定金额 1000，应该买 333 股 -> 向下取整到 300 股
        shares = strategy.calculate_shares(price=3.0, lot_size=100)
        self.assertEqual(shares, 300)
    
    def test_calculate_shares_zero_price(self):
        """测试股数计算：价格为零或负数"""
        strategy = FixedAmountDecision(fixed_amount=1000.0)
        
        shares = strategy.calculate_shares(price=0.0, lot_size=100)
        self.assertEqual(shares, 0)
        
        shares = strategy.calculate_shares(price=-10.0, lot_size=100)
        self.assertEqual(shares, 0)
    
    def test_different_fixed_amounts(self):
        """测试不同的固定金额"""
        # 固定金额 500
        strategy = FixedAmountDecision(fixed_amount=500.0)
        shares = strategy.calculate_shares(price=5.0, lot_size=100)
        self.assertEqual(shares, 100)  # 500/5 = 100
        
        # 固定金额 2000
        strategy = FixedAmountDecision(fixed_amount=2000.0)
        shares = strategy.calculate_shares(price=5.0, lot_size=100)
        self.assertEqual(shares, 400)  # 2000/5 = 400

    def test_calculate_shares_with_fund_unit(self):
        """测试基金场景：支持按0.01份进行买入。"""
        strategy = FixedAmountDecision(fixed_amount=1000.0)
        shares = strategy.calculate_shares(price=1.234, lot_size=0.01)
        self.assertAlmostEqual(shares, 810.37, places=2)

    def test_calculate_shares_invalid_lot_size(self):
        """测试非法交易单位时返回0。"""
        strategy = FixedAmountDecision(fixed_amount=1000.0)
        shares = strategy.calculate_shares(price=10.0, lot_size=0)
        self.assertEqual(shares, 0.0)


class TestFixedAmountSimulation(unittest.TestCase):
    """测试定投策略的完整模拟"""
    
    def test_basic_simulation(self):
        """测试基本的定投模拟"""
        df = make_test_df(10, start_price=10.0)
        sim = Simulator(lot_size=100, init_cash=100000.0)
        strategy = FixedAmountDecision(fixed_amount=1000.0)
        
        result = sim.simulate(df=df, strategy=strategy, symbol="TEST")
        
        # 验证返回结构
        self.assertIn('symbol', result)
        self.assertIn('init_cash', result)
        self.assertIn('cash', result)
        self.assertIn('shares', result)
        self.assertIn('total_value', result)
        self.assertIn('trades', result)
        
        # 验证策略执行
        self.assertEqual(result['symbol'], "TEST")
        self.assertEqual(result['init_cash'], 100000.0)
        
        # 价格从 10 到 19，每次投入 1000 元
        # 第1天：1000/10 = 100 股（1手）✓
        # 第2天：1000/11 = 90 股（0手）✗
        # 第3天：1000/12 = 83 股（0手）✗
        # ... 后面的价格更高，都不足1手
        # 所以应该只成功交易1次
        self.assertEqual(result['trades'], 1)
        self.assertEqual(result['shares'], 100)  # 持有100股
    
    def test_insufficient_funds(self):
        """测试资金不足的情况"""
        df = make_test_df(10, start_price=1000.0)  # 价格很高
        sim = Simulator(lot_size=100, init_cash=5000.0)  # 初始资金只有 5000
        strategy = FixedAmountDecision(fixed_amount=200000.0)  # 固定金额 200000
        
        result = sim.simulate(df=df, strategy=strategy, symbol="TEST")
        
        # 由于资金不足，无法交易
        self.assertEqual(result['trades'], 0)
        self.assertEqual(result['shares'], 0)
        self.assertEqual(result['cash'], 5000.0)
    
    def test_multiple_trades(self):
        """测试多次成功交易"""
        # 价格保持在低位，每天都能买入
        dates = pd.date_range(end="2023-12-31", periods=5, freq="D")
        data = {
            "date": dates,
            "open": [10.0, 10.0, 10.0, 10.0, 10.0],
            "high": [11.0, 11.0, 11.0, 11.0, 11.0],
            "low": [9.0, 9.0, 9.0, 9.0, 9.0],
            "close": [10.0, 10.0, 10.0, 10.0, 10.0],
            "volume": [1000, 1000, 1000, 1000, 1000],
        }
        df = pd.DataFrame(data)
        
        sim = Simulator(lot_size=100, init_cash=100000.0)
        strategy = FixedAmountDecision(fixed_amount=1000.0)
        
        result = sim.simulate(df=df, strategy=strategy, symbol="TEST")
        
        # 5天，每天都能买入 100 股
        self.assertEqual(result['trades'], 5)
        self.assertEqual(result['shares'], 500)  # 5 * 100
        # 花费：5 * 1000 = 5000
        self.assertEqual(result['cash'], 100000.0 - 5000.0)
    
    def test_verbose_output(self):
        """测试详细输出模式"""
        df = make_test_df(3, start_price=10.0)
        sim = Simulator(lot_size=100, init_cash=100000.0, verbose=True)
        strategy = FixedAmountDecision(fixed_amount=1000.0)
        
        # 这个测试主要确保 verbose 模式不会出错
        result = sim.simulate(df=df, strategy=strategy, symbol="TEST")
        self.assertIsNotNone(result)
    
    @patch('simulator.simulator.get_data')
    def test_simulate_fixed_amount_function(self, mock_get_data):
        """测试 simulate_fixed_amount 便捷函数"""
        # Mock 数据获取
        mock_df = make_test_df(5, start_price=10.0)
        mock_get_data.return_value = mock_df
        
        result = simulate_fixed_amount(
            symbol="600900",
            start_date="20230101",
            end_date="20231231",
            fixed_amount=1000.0,
            lot_size=100,
            init_cash=100000.0
        )
        
        # 验证调用了数据获取
        mock_get_data.assert_called_once()
        
        # 验证返回结果
        self.assertIn('symbol', result)
        self.assertEqual(result['symbol'], "600900")
        self.assertIn('trades', result)
    
    @patch('simulator.simulator.get_data')
    def test_simulate_fixed_amount_no_data(self, mock_get_data):
        """测试没有数据的情况"""
        mock_get_data.return_value = None
        
        with self.assertRaises(RuntimeError) as ctx:
            simulate_fixed_amount(
                symbol="600900",
                start_date="20230101",
                end_date="20231231"
            )
        self.assertIn("未获取到数据", str(ctx.exception))


class TestFixedAmountWithDifferentPrices(unittest.TestCase):
    """测试定投策略在不同价格场景下的表现"""
    
    def test_declining_price(self):
        """测试价格下跌场景（定投的优势）"""
        # 价格从 20 降到 10
        dates = pd.date_range(end="2023-12-31", periods=5, freq="D")
        data = {
            "date": dates,
            "open": [20.0, 17.5, 15.0, 12.5, 10.0],
            "high": [21.0, 18.0, 16.0, 13.0, 11.0],
            "low": [19.0, 17.0, 14.0, 12.0, 9.0],
            "close": [20.0, 17.5, 15.0, 12.5, 10.0],
            "volume": [1000, 1000, 1000, 1000, 1000],
        }
        df = pd.DataFrame(data)
        
        sim = Simulator(lot_size=100, init_cash=100000.0)
        strategy = FixedAmountDecision(fixed_amount=2000.0)
        
        result = sim.simulate(df=df, strategy=strategy, symbol="TEST")
        
        # 第1天：2000/20 = 100 股 ✓
        # 第2天：2000/17.5 = 114 股 -> 100 股 ✓
        # 第3天：2000/15 = 133 股 -> 100 股 ✓
        # 第4天：2000/12.5 = 160 股 -> 100 股 ✓
        # 第5天：2000/10 = 200 股 -> 200 股 ✓
        self.assertEqual(result['trades'], 5)
        self.assertEqual(result['shares'], 600)  # 100+100+100+100+200
    
    def test_rising_price(self):
        """测试价格上涨场景"""
        # 价格从 10 涨到 50
        dates = pd.date_range(end="2023-12-31", periods=5, freq="D")
        data = {
            "date": dates,
            "open": [10.0, 20.0, 30.0, 40.0, 50.0],
            "high": [11.0, 21.0, 31.0, 41.0, 51.0],
            "low": [9.0, 19.0, 29.0, 39.0, 49.0],
            "close": [10.0, 20.0, 30.0, 40.0, 50.0],
            "volume": [1000, 1000, 1000, 1000, 1000],
        }
        df = pd.DataFrame(data)
        
        sim = Simulator(lot_size=100, init_cash=100000.0)
        strategy = FixedAmountDecision(fixed_amount=1000.0)
        
        result = sim.simulate(df=df, strategy=strategy, symbol="TEST")
        
        # 第1天：1000/10 = 100 股 ✓
        # 第2天：1000/20 = 50 股 -> 0 股 ✗
        # 后面的价格更高，都不足1手
        self.assertEqual(result['trades'], 1)
        self.assertEqual(result['shares'], 100)


if __name__ == '__main__':
    unittest.main()
