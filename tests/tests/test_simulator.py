"""
测试 simulator 模块：验证不同策略的模拟交易功能
"""
import unittest
from unittest.mock import patch
import pandas as pd

from simulator.simulator import Simulator, simulate_mean_cost, simulate_sma
from solver.mean_cost_strategy import MeanCostDecision
from solver.sma_strategy import SmaDecision


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


class TestSimulator(unittest.TestCase):
    """测试 Simulator 基础类"""
    
    def test_simulator_init(self):
        """测试 Simulator 初始化"""
        sim = Simulator(lot_size=100, init_cash=100000.0)
        self.assertEqual(sim.lot_size, 100)
        self.assertEqual(sim.init_cash, 100000.0)
    
    def test_simulator_requires_dataframe(self):
        """测试 Simulator 需要 DataFrame"""
        sim = Simulator()
        with self.assertRaises(RuntimeError) as ctx:
            sim.simulate(df=None, strategy=MeanCostDecision())
        self.assertIn("需要传入数据", str(ctx.exception))
    
    def test_simulator_empty_dataframe(self):
        """测试 Simulator 处理空 DataFrame"""
        sim = Simulator()
        # Create empty dataframe with proper columns to pass initial sort
        empty_df = pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume'])
        with self.assertRaises(RuntimeError) as ctx:
            sim.simulate(df=empty_df, strategy=MeanCostDecision())
        self.assertIn("数据为空", str(ctx.exception))


class TestMeanCostStrategy(unittest.TestCase):
    """测试 MeanCostDecision 策略的模拟交易"""
    
    def test_mean_cost_decision_first_buy(self):
        """测试均值成本策略：持仓为0时应该买入"""
        decision = MeanCostDecision()
        action = decision.decide(open_price=100.0, shares=0)
        self.assertEqual(action, 'buy')
    
    def test_mean_cost_decision_buy_below_avg(self):
        """测试均值成本策略：开盘价低于平均成本时买入"""
        decision = MeanCostDecision()
        action = decision.decide(open_price=95.0, avg_cost=100.0, shares=100)
        self.assertEqual(action, 'buy')
    
    def test_mean_cost_decision_sell_above_avg(self):
        """测试均值成本策略：开盘价高于平均成本时卖出"""
        decision = MeanCostDecision()
        action = decision.decide(open_price=105.0, avg_cost=100.0, shares=100)
        self.assertEqual(action, 'sell')
    
    def test_mean_cost_decision_hold_at_avg(self):
        """测试均值成本策略：开盘价等于平均成本时持有"""
        decision = MeanCostDecision()
        action = decision.decide(open_price=100.0, avg_cost=100.0, shares=100)
        self.assertIsNone(action)
    
    def test_mean_cost_simulator_basic(self):
        """测试均值成本策略的基本模拟"""
        df = make_test_df(10, start_price=100.0)
        sim = Simulator(lot_size=100, init_cash=100000.0)
        strategy = MeanCostDecision()
        
        result = sim.simulate(df=df, strategy=strategy, symbol="TEST")
        
        # 验证返回结构
        self.assertIn('symbol', result)
        self.assertIn('init_cash', result)
        self.assertIn('cash', result)
        self.assertIn('shares', result)
        self.assertIn('total_value', result)
        self.assertIn('trades', result)
        self.assertIn('history', result)
        self.assertIn('trades_list', result)
        
        # 验证初始资金
        self.assertEqual(result['init_cash'], 100000.0)
        self.assertEqual(result['symbol'], "TEST")
        
        # 验证产生了交易
        self.assertGreater(result['trades'], 0)
    
    def test_mean_cost_simulator_multiple_trades(self):
        """测试均值成本策略产生多次交易"""
        # 创建价格波动的数据：先涨后跌
        dates = pd.date_range(end="2023-12-31", periods=20, freq="D")
        prices = [100 + i*2 if i < 10 else 120 - (i-10)*2 for i in range(20)]
        df = pd.DataFrame({
            "date": dates,
            "open": prices,
            "high": [p + 1 for p in prices],
            "low": [p - 1 for p in prices],
            "close": prices,
            "volume": [1000] * 20,
        })
        
        sim = Simulator(lot_size=100, init_cash=50000.0)
        strategy = MeanCostDecision()
        result = sim.simulate(df=df, strategy=strategy, symbol="TEST")
        
        # 应该有多次买入和卖出
        self.assertGreater(result['trades'], 2)
        self.assertGreater(len(result['trades_list']), 2)
        
        # 验证 trades_list 包含买卖记录
        has_buy = any(t['action'] == 'buy' for t in result['trades_list'])
        has_sell = any(t['action'] == 'sell' for t in result['trades_list'])
        self.assertTrue(has_buy)
        self.assertTrue(has_sell)
    
    def test_max_capital_used_tracking(self):
        """测试最大占用资金的追踪"""
        # 创建一个简单的场景：持续买入导致现金减少
        dates = pd.date_range(end="2023-12-31", periods=5, freq="D")
        df = pd.DataFrame({
            "date": dates,
            "open": [100.0, 90.0, 80.0, 70.0, 60.0],  # 持续下跌，会持续买入
            "high": [101.0, 91.0, 81.0, 71.0, 61.0],
            "low": [99.0, 89.0, 79.0, 69.0, 59.0],
            "close": [100.0, 90.0, 80.0, 70.0, 60.0],
            "volume": [1000] * 5,
        })
        
        init_cash = 50000.0
        sim = Simulator(lot_size=100, init_cash=init_cash)
        strategy = MeanCostDecision()
        result = sim.simulate(df=df, strategy=strategy, symbol="TEST")
        
        # 验证返回结果包含最大占用资金
        self.assertIn('max_capital_used', result)
        self.assertIn('min_cash', result)
        
        # 最大占用资金应该 = 初始资金 - 最小现金
        self.assertAlmostEqual(
            result['max_capital_used'],
            init_cash - result['min_cash'],
            places=2
        )
        
        # 最大占用资金应该大于0（因为有交易发生）
        self.assertGreater(result['max_capital_used'], 0)
        
        # 最大占用资金不应超过初始资金
        self.assertLessEqual(result['max_capital_used'], init_cash)
        
        # 最小现金应该小于初始资金（因为有买入）
        self.assertLess(result['min_cash'], init_cash)


class TestSmaStrategy(unittest.TestCase):
    """测试 SmaDecision 策略的模拟交易"""
    
    def test_sma_decision_buy_above_sma(self):
        """测试 SMA 策略：收盘价高于 SMA 时买入"""
        df = make_test_df(25, start_price=100.0)
        df['sma'] = df['close'].rolling(window=20, min_periods=1).mean()
        
        strategy = SmaDecision(period=20, df=df)
        # 获取最后一天的数据
        last_row = df.iloc[-1]
        action = strategy.decide(
            open_price=last_row['open'],
            close_price=last_row['close'],
            shares=0,
            date=last_row['date']
        )
        # 价格持续上涨，最后应该高于 SMA
        self.assertEqual(action, 'buy')
    
    def test_sma_decision_sell_below_sma(self):
        """测试 SMA 策略：持仓且收盘价低于 SMA 时卖出"""
        # 创建先涨后跌的数据
        dates = pd.date_range(end="2023-12-31", periods=25, freq="D")
        prices = [100 + i*2 if i < 15 else 130 - (i-15)*3 for i in range(25)]
        df = pd.DataFrame({
            "date": dates,
            "open": prices,
            "high": [p + 1 for p in prices],
            "low": [p - 1 for p in prices],
            "close": prices,
            "volume": [1000] * 25,
        })
        df['sma'] = df['close'].rolling(window=20, min_periods=1).mean()
        
        strategy = SmaDecision(period=20, df=df)
        last_row = df.iloc[-1]
        action = strategy.decide(
            open_price=last_row['open'],
            close_price=last_row['close'],
            shares=100,
            date=last_row['date']
        )
        # 价格下跌应该低于 SMA，持仓应该卖出
        self.assertEqual(action, 'sell')
    
    def test_sma_decision_no_dataframe(self):
        """测试 SMA 策略没有 DataFrame 时返回 None"""
        strategy = SmaDecision(period=20, df=None)
        action = strategy.decide(open_price=100.0, close_price=105.0, shares=0)
        self.assertIsNone(action)
    
    def test_sma_simulator_basic(self):
        """测试 SMA 策略的基本模拟"""
        df = make_test_df(30, start_price=100.0)
        
        sim = Simulator(lot_size=100, init_cash=100000.0)
        result = simulate_sma(symbol="TEST", df=df, period=20, lot_size=100, init_cash=100000.0)
        
        # 验证返回结构
        self.assertIn('symbol', result)
        self.assertIn('init_cash', result)
        self.assertIn('cash', result)
        self.assertIn('shares', result)
        self.assertIn('total_value', result)
        self.assertIn('trades', result)
        
        # 验证初始资金
        self.assertEqual(result['init_cash'], 100000.0)
        self.assertEqual(result['symbol'], "TEST")


class TestSimulatorWithDifferentParameters(unittest.TestCase):
    """测试不同参数下的模拟器行为"""
    
    def test_different_lot_sizes(self):
        """测试不同的交易手数"""
        df = make_test_df(10)
        strategy = MeanCostDecision()
        
        # 测试 100 手
        sim1 = Simulator(lot_size=100, init_cash=100000.0)
        result1 = sim1.simulate(df=df, strategy=strategy)
        
        # 测试 200 手
        sim2 = Simulator(lot_size=200, init_cash=100000.0)
        result2 = sim2.simulate(df=df, strategy=strategy)
        
        # 手数不同，交易次数可能不同（因为资金限制）
        self.assertIsInstance(result1['trades'], int)
        self.assertIsInstance(result2['trades'], int)
    
    def test_different_init_cash(self):
        """测试不同的初始资金"""
        df = make_test_df(10)
        strategy = MeanCostDecision()
        
        # 测试 10000 元
        sim1 = Simulator(lot_size=100, init_cash=10000.0)
        result1 = sim1.simulate(df=df, strategy=strategy)
        
        # 测试 100000 元
        sim2 = Simulator(lot_size=100, init_cash=100000.0)
        result2 = sim2.simulate(df=df, strategy=strategy)
        
        # 初始资金不同，最终资金应该不同
        self.assertNotEqual(result1['init_cash'], result2['init_cash'])
        self.assertEqual(result1['init_cash'], 10000.0)
        self.assertEqual(result2['init_cash'], 100000.0)
    
    def test_insufficient_cash_prevents_buy(self):
        """测试资金不足时无法买入"""
        df = make_test_df(5, start_price=1000.0)
        strategy = MeanCostDecision()
        
        # 初始资金只有 5000，无法购买价格 1000 * 100 手
        sim = Simulator(lot_size=100, init_cash=5000.0)
        result = sim.simulate(df=df, strategy=strategy)
        
        # 应该没有交易
        self.assertEqual(result['trades'], 0)
        self.assertEqual(result['shares'], 0)
        self.assertEqual(result['cash'], 5000.0)


class TestIntegratedSimulation(unittest.TestCase):
    """集成测试：测试完整的模拟流程"""
    
    @patch('source.data_provider.get_data')
    def test_simulate_mean_cost_end_to_end(self, mock_get_data):
        """测试 simulate_mean_cost 端到端流程"""
        mock_get_data.return_value = make_test_df(15)
        
        result = simulate_mean_cost(
            symbol="600900",
            start_date="20230101",
            end_date="20231231",
            lot_size=100,
            init_cash=100000.0,
            source="auto"
        )
        
        # 验证结果
        self.assertEqual(result['symbol'], "600900")
        self.assertIn('start_date', result)
        self.assertIn('end_date', result)
        self.assertIn('total_value', result)
        self.assertIn('realized_pl', result)
        self.assertIn('unrealized_pl', result)
    
    def test_simulate_sma_end_to_end(self):
        """测试 simulate_sma 端到端流程"""
        df = make_test_df(30)
        
        result = simulate_sma(
            symbol="600900",
            df=df,
            period=20,
            lot_size=100,
            init_cash=100000.0
        )
        
        # 验证结果
        self.assertEqual(result['symbol'], "600900")
        self.assertIn('start_date', result)
        self.assertIn('end_date', result)
        self.assertIn('total_value', result)


class TestProfitLossCalculation(unittest.TestCase):
    """测试盈亏计算"""
    
    def test_realized_profit_on_sell(self):
        """测试卖出时实现盈利"""
        # 创建价格上涨的数据
        dates = pd.date_range(end="2023-12-31", periods=5, freq="D")
        df = pd.DataFrame({
            "date": dates,
            "open": [100, 101, 102, 103, 104],
            "high": [101, 102, 103, 104, 105],
            "low": [99, 100, 101, 102, 103],
            "close": [100, 101, 102, 103, 104],
            "volume": [1000] * 5,
        })
        
        sim = Simulator(lot_size=100, init_cash=50000.0)
        strategy = MeanCostDecision()
        result = sim.simulate(df=df, strategy=strategy)
        
        # 应该有实现盈亏
        self.assertIn('realized_pl', result)
        self.assertIsInstance(result['realized_pl'], (int, float))
    
    def test_unrealized_profit_on_hold(self):
        """测试持仓时未实现盈利"""
        df = make_test_df(5, start_price=100.0)
        
        sim = Simulator(lot_size=100, init_cash=50000.0)
        strategy = MeanCostDecision()
        result = sim.simulate(df=df, strategy=strategy)
        
        # 应该有未实现盈亏
        self.assertIn('unrealized_pl', result)
        self.assertIsInstance(result['unrealized_pl'], (int, float))


if __name__ == '__main__':
    unittest.main()
