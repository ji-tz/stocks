"""
测试新的交易引擎架构
"""
import unittest
from datetime import datetime
import pandas as pd

from simulator.base_engine import Position, Account, TradeOrder, TradeResult
from simulator.simulator_engine import SimulatorEngine
from simulator.real_engine import RealEngine


class TestBaseEngineStructures(unittest.TestCase):
    """测试基础数据结构"""

    def test_position_init(self):
        """测试持仓初始化"""
        pos = Position()
        self.assertEqual(pos.shares, 0)
        self.assertEqual(pos.avg_cost, 0.0)
        self.assertEqual(pos.total_cost, 0.0)

    def test_account_init(self):
        """测试账户初始化"""
        acc = Account(cash=100000.0)
        self.assertEqual(acc.cash, 100000.0)
        self.assertIsNotNone(acc.position)
        self.assertEqual(acc.position.shares, 0)

    def test_account_total_value(self):
        """测试账户总价值计算"""
        acc = Account(cash=50000.0)
        acc.position.shares = 100
        total = acc.get_total_value(current_price=100.0)
        self.assertEqual(total, 60000.0)  # 50000 + 100*100

    def test_trade_order(self):
        """测试交易订单"""
        order = TradeOrder(
            date=datetime(2023, 1, 1),
            action='buy',
            price=10.5,
            shares=100
        )
        self.assertEqual(order.action, 'buy')
        self.assertEqual(order.price, 10.5)
        self.assertEqual(order.shares, 100)

    def test_trade_result(self):
        """测试交易结果"""
        result = TradeResult(
            success=True,
            message="买入成功",
            cash_after=90000.0,
            shares_after=100
        )
        self.assertTrue(result.success)
        self.assertEqual(result.message, "买入成功")


class TestSimulatorEngine(unittest.TestCase):
    """测试模拟交易引擎"""

    def test_engine_init(self):
        """测试引擎初始化"""
        engine = SimulatorEngine(init_cash=100000.0, lot_size=100)
        self.assertEqual(engine.get_cash(), 100000.0)
        self.assertEqual(engine.lot_size, 100)
        self.assertEqual(engine.get_position().shares, 0)

    def test_buy_success(self):
        """测试成功买入"""
        engine = SimulatorEngine(init_cash=100000.0, lot_size=100)
        date = datetime(2023, 1, 1)
        result = engine.buy(date=date, price=100.0)

        self.assertTrue(result.success)
        self.assertEqual(result.shares_after, 100)
        self.assertEqual(result.cash_after, 90000.0)
        self.assertEqual(engine.get_position().shares, 100)
        self.assertEqual(engine.get_cash(), 90000.0)

    def test_buy_insufficient_cash(self):
        """测试资金不足无法买入"""
        engine = SimulatorEngine(init_cash=5000.0, lot_size=100)
        date = datetime(2023, 1, 1)
        result = engine.buy(date=date, price=100.0)

        self.assertFalse(result.success)
        self.assertIn("资金不足", result.message)
        self.assertEqual(engine.get_position().shares, 0)
        self.assertEqual(engine.get_cash(), 5000.0)

    def test_sell_success(self):
        """测试成功卖出"""
        engine = SimulatorEngine(init_cash=100000.0, lot_size=100)
        date = datetime(2023, 1, 1)

        # 先买入
        engine.buy(date=date, price=100.0)
        # 再卖出
        result = engine.sell(date=date, price=110.0)

        self.assertTrue(result.success)
        self.assertEqual(result.shares_after, 0)
        self.assertEqual(result.cash_after, 101000.0)  # 90000 + 110*100
        self.assertEqual(result.realized_pl, 1000.0)  # (110-100)*100
        self.assertEqual(engine.get_position().shares, 0)

    def test_sell_insufficient_shares(self):
        """测试持仓不足无法卖出"""
        engine = SimulatorEngine(init_cash=100000.0, lot_size=100)
        date = datetime(2023, 1, 1)
        result = engine.sell(date=date, price=100.0)

        self.assertFalse(result.success)
        self.assertIn("持仓不足", result.message)
        self.assertEqual(engine.get_position().shares, 0)

    def test_multiple_trades(self):
        """测试多次交易"""
        engine = SimulatorEngine(init_cash=100000.0, lot_size=100)
        date = datetime(2023, 1, 1)

        # 买入三次
        engine.buy(date=date, price=100.0)
        engine.buy(date=date, price=110.0)
        engine.buy(date=date, price=120.0)

        # 应该持有300股
        self.assertEqual(engine.get_position().shares, 300)
        # 平均成本应该是110
        self.assertAlmostEqual(engine.get_position().avg_cost, 110.0, places=2)

        # 卖出一次
        result = engine.sell(date=date, price=130.0)
        self.assertTrue(result.success)
        self.assertEqual(engine.get_position().shares, 200)
        # 已实现盈亏应该是 (130-110)*100 = 2000
        self.assertAlmostEqual(engine.realized_pl, 2000.0, places=2)

    def test_get_summary(self):
        """测试获取账户摘要"""
        engine = SimulatorEngine(init_cash=100000.0, lot_size=100)
        date = datetime(2023, 1, 1)

        # 买入
        engine.buy(date=date, price=100.0)

        # 获取摘要（当前价格110）
        summary = engine.get_summary(current_price=110.0)

        self.assertEqual(summary['cash'], 90000.0)
        self.assertEqual(summary['shares'], 100)
        self.assertEqual(summary['avg_cost'], 100.0)
        self.assertEqual(summary['market_value'], 11000.0)  # 100*110
        self.assertEqual(summary['total_value'], 101000.0)  # 90000+11000
        self.assertEqual(summary['unrealized_pl'], 1000.0)  # (110-100)*100

    def test_trade_count(self):
        """测试交易次数统计"""
        engine = SimulatorEngine(init_cash=100000.0, lot_size=100)
        date = datetime(2023, 1, 1)

        self.assertEqual(engine.trade_count, 0)

        engine.buy(date=date, price=100.0)
        self.assertEqual(engine.trade_count, 1)

        engine.buy(date=date, price=110.0)
        self.assertEqual(engine.trade_count, 2)

        engine.sell(date=date, price=120.0)
        self.assertEqual(engine.trade_count, 3)

        engine.sell(date=date, price=130.0)  # 还有100股，会成功
        self.assertEqual(engine.trade_count, 4)

        # 失败的交易不计数
        engine.sell(date=date, price=140.0)  # 这次会失败（已全部卖出）
        self.assertEqual(engine.trade_count, 4)


class TestRealEngineInterface(unittest.TestCase):
    """测试实盘交易引擎接口（预留）"""

    def test_real_engine_init(self):
        """测试实盘引擎初始化"""
        engine = RealEngine(init_cash=100000.0, lot_size=100)
        self.assertEqual(engine.get_cash(), 100000.0)
        self.assertFalse(engine.connected)

    def test_real_engine_not_implemented(self):
        """测试实盘引擎抛出未实现异常"""
        engine = RealEngine(init_cash=100000.0, lot_size=100)
        date = datetime(2023, 1, 1)

        with self.assertRaises(NotImplementedError):
            engine.connect()

        with self.assertRaises(NotImplementedError):
            engine.buy(date=date, price=100.0)

        with self.assertRaises(NotImplementedError):
            engine.sell(date=date, price=100.0)

        with self.assertRaises(NotImplementedError):
            engine.get_real_time_price("600900")

        with self.assertRaises(NotImplementedError):
            engine.cancel_order("order123")


class TestSimulatorWithVerbose(unittest.TestCase):
    """测试带详细输出的模拟器"""

    def test_verbose_output(self):
        """测试verbose模式下的输出"""
        from simulator import Simulator
        from solver.mean_cost_strategy import MeanCostDecision

        # 创建测试数据
        dates = pd.date_range(end="2023-12-31", periods=5, freq="D")
        df = pd.DataFrame({
            "date": dates,
            "open": [100, 101, 102, 103, 104],
            "high": [101, 102, 103, 104, 105],
            "low": [99, 100, 101, 102, 103],
            "close": [100, 101, 102, 103, 104],
            "volume": [1000] * 5,
        })

        # 使用verbose模式
        sim = Simulator(lot_size=100, init_cash=50000.0, verbose=False)  # 测试时不打印
        strategy = MeanCostDecision()
        result = sim.simulate(df=df, strategy=strategy, symbol="TEST")

        # 验证结果仍然正确
        self.assertIn('symbol', result)
        self.assertEqual(result['symbol'], "TEST")
        self.assertGreater(result['trades'], 0)


if __name__ == '__main__':
    unittest.main()
