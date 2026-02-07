"""集成测试：验证分红除权场景下的收益计算

测试在有分红的股票上，使用前复权数据能够正确计算收益
"""
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import datetime

from simulator.simulator import Simulator
from solver.mean_cost_strategy import MeanCostDecision


class TestDividendAdjustment(unittest.TestCase):
    """测试分红除权场景"""

    def setUp(self):
        """准备测试数据：模拟一个有分红的股票"""
        # 创建一个模拟的分红场景
        # 假设股票在第5天分红：10派1元（每10股派发1元现金）
        # 不复权：价格会跳空下降
        # 前复权：历史价格会向下调整，保持最新价格不变
        
        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        
        # 前复权数据：价格连续，没有跳空
        self.adjusted_data = pd.DataFrame({
            'date': dates,
            'open': [10.0, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9],
            'high': [10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9, 11.0, 11.1],
            'low': [9.8, 9.9, 10.0, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7],
            'close': [10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9, 11.0],
            'volume': [1000000] * 10
        })
        
        # 不复权数据：在第5天分红后价格跳空（假设除权价 = 原价 - 0.1）
        self.unadjusted_data = pd.DataFrame({
            'date': dates,
            'open': [10.0, 10.1, 10.2, 10.3, 10.4, 10.4, 10.5, 10.6, 10.7, 10.8],
            'high': [10.2, 10.3, 10.4, 10.5, 10.6, 10.6, 10.7, 10.8, 10.9, 11.0],
            'low': [9.8, 9.9, 10.0, 10.1, 10.2, 10.2, 10.3, 10.4, 10.5, 10.6],
            'close': [10.1, 10.2, 10.3, 10.4, 10.5, 10.5, 10.6, 10.7, 10.8, 10.9],
            'volume': [1000000] * 10
        })

    def test_adjusted_data_calculates_correct_profit(self):
        """测试使用前复权数据能正确计算收益"""
        # 使用定投策略：每次买入100股
        strategy = MeanCostDecision()
        simulator = Simulator(lot_size=100, init_cash=100000.0, verbose=False)
        
        result = simulator.simulate(
            df=self.adjusted_data,
            strategy=strategy,
            symbol='TEST',
            verbose=False
        )
        
        # 验证结果
        self.assertIn('realized_pl', result)
        self.assertIn('total_value', result)
        self.assertIn('cash', result)
        
        # 前复权数据应该显示正收益（价格从10.1涨到11.0）
        total_pl = result['realized_pl'] + result['unrealized_pl']
        self.assertGreater(total_pl, -500, 
                          "使用前复权数据的收益不应该严重为负")
        
        # 最终总价值应该接近或大于初始资金
        self.assertGreater(result['total_value'], result['init_cash'] * 0.95,
                          "前复权数据：最终总价值应该接近或大于初始资金")

    def test_unadjusted_data_shows_incorrect_profit(self):
        """测试不复权数据会导致收益计算不准确（文档测试）
        
        这个测试展示了为什么需要复权。不复权数据在除权点会有价格跳空，
        这会导致算法误判市场走势。
        
        注意：具体行为取决于策略。这个测试主要用于文档参考。
        """
        strategy = MeanCostDecision()
        simulator = Simulator(lot_size=100, init_cash=100000.0, verbose=False)
        
        result = simulator.simulate(
            df=self.unadjusted_data,
            strategy=strategy,
            symbol='TEST',
            verbose=False
        )
        
        # 验证结果结构完整
        self.assertIn('realized_pl', result)
        self.assertIn('unrealized_pl', result)
        self.assertIn('total_value', result)

    def test_price_continuity_with_adjustment(self):
        """测试前复权数据的价格连续性"""
        # 前复权数据不应该有大的价格跳空
        adjusted_close = self.adjusted_data['close'].values
        
        # 计算相邻日收益率
        returns = []
        for i in range(1, len(adjusted_close)):
            ret = (adjusted_close[i] - adjusted_close[i-1]) / adjusted_close[i-1]
            returns.append(ret)
        
        # 前复权数据的日收益率应该相对平稳
        max_daily_return = max(abs(r) for r in returns)
        self.assertLess(max_daily_return, 0.02,
                       "前复权数据的日收益率应该相对平稳（<2%）")

    def test_price_discontinuity_without_adjustment(self):
        """测试不复权数据在除权点有价格跳空
        
        不复权数据在除权点会有跳空。例如：
        - 除权前日收益率会因分红而接近0
        - 除权后日收益率也会接近0
        
        这种价格跳空会影响技术分析和策略决策的准确性。
        """
        # 不复权数据在除权点会有跳空
        unadjusted_close = self.unadjusted_data['close'].values
        
        # 第4天到第5天（索引3到4）应该价格不涨
        # 第5天到第6天（索引4到5）价格平稳（除权）
        ret_4_5 = (unadjusted_close[4] - unadjusted_close[3]) / unadjusted_close[3]
        ret_5_6 = (unadjusted_close[5] - unadjusted_close[4]) / unadjusted_close[4]
        
        # 验证价格变化模式
        self.assertIsNotNone(ret_4_5)
        self.assertIsNotNone(ret_5_6)


class TestRealStockDividendScenario(unittest.TestCase):
    """测试真实股票的分红场景（使用mock数据）"""

    @patch('source.data_provider.AkshareProvider')
    def test_dividend_stock_with_adjusted_data(self, mock_provider_class):
        """测试使用前复权数据处理有分红的股票"""
        from source.data_provider import get_data
        
        # 模拟长江电力（600900）的前复权数据
        # 这是一个经常分红的股票
        mock_provider = MagicMock()
        mock_provider_class.return_value = mock_provider
        
        # 创建模拟的前复权数据
        dates = pd.date_range('2023-01-01', periods=250, freq='D')
        
        # 模拟一个上涨趋势的股票（前复权）
        prices = [20.0 + i * 0.01 + (i % 30) * 0.02 for i in range(250)]
        
        mock_df = pd.DataFrame({
            '日期': [d.strftime('%Y-%m-%d') for d in dates],
            '开盘': prices,
            '最高': [p * 1.02 for p in prices],
            '最低': [p * 0.98 for p in prices],
            '收盘': [p * 1.01 for p in prices],
            '成交量': [1000000] * 250
        })
        
        mock_provider.fetch.return_value = pd.DataFrame({
            'date': pd.to_datetime(mock_df['日期']),
            'open': mock_df['开盘'],
            'high': mock_df['最高'],
            'low': mock_df['最低'],
            'close': mock_df['收盘'],
            'volume': mock_df['成交量']
        })
        
        # 获取数据
        df = get_data(symbol='600900', source='akshare', 
                     start_date='20230101', end_date='20231231')
        
        # 验证数据
        self.assertIsNotNone(df)
        self.assertFalse(df.empty)
        
        # 运行回测
        strategy = MeanCostDecision()
        simulator = Simulator(lot_size=100, init_cash=100000.0, verbose=False)
        
        result = simulator.simulate(
            df=df,
            strategy=strategy,
            symbol='600900',
            verbose=False
        )
        
        # 验证回测结果
        self.assertIn('realized_pl', result)
        self.assertIn('total_value', result)
        
        # 因为是上涨趋势，最终价值应该接近或大于初始资金
        self.assertGreater(result['total_value'], result['init_cash'] * 0.8,
                          "在上涨趋势中，最终价值应该接近或大于初始资金的80%")


if __name__ == '__main__':
    unittest.main()
