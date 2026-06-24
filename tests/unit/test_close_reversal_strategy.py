"""单元测试：收盘反转策略（Close Reversal Strategy）

测试用例覆盖三种信号场景：
1. 当日下跌 → BUY 信号
2. 当日上涨且有持仓 → SELL 信号
3. 当日持平 → 无信号（None）
4. 当日上涨但无持仓 → 无信号（不卖空）
5. 最小变动百分比阈值过滤
"""
import unittest

import pandas as pd

from strategy.close_reversal_strategy import (
    CloseReversalDecision,
    create_strategy,
    prepare_backtest_data,
    validate_strategy_parameters,
)


class TestCloseReversalDecision(unittest.TestCase):
    """策略决策器的单一功能测试。"""

    def setUp(self):
        """构造标准测试数据集。

        价格序列：100 → 101（涨1%）→ 99（跌约1.98%）→ 99（持平）
        """
        dates = pd.date_range(start="2023-01-01", periods=3, freq="D")
        self.df = pd.DataFrame({
            "date": dates,
            "open": [100.0, 101.0, 99.0],
            "high": [101.0, 102.0, 100.0],
            "low": [99.0, 100.0, 98.0],
            "close": [100.0, 101.0, 99.0],
            "volume": [1000, 1000, 1000],
        })

    def test_buy_signal_when_close_drops(self):
        """当收盘价下跌（前一日100→今日99）时，应输出 buy 信号。"""
        strategy = CloseReversalDecision(df=self.df)
        # 第3天：close=99, 前一日close=101 → 下跌约 -1.98% → BUY
        action = strategy.decide(
            open_price=99.0, close_price=99.0,
            shares=0, date=self.df.iloc[2]["date"],
        )
        self.assertEqual(action, "buy")

    def test_sell_signal_when_close_rises_and_holding(self):
        """当收盘价上涨且有持仓时，应输出 sell 信号。"""
        strategy = CloseReversalDecision(df=self.df)
        # 第2天：close=101, 前一日close=100 → 上涨1% → SELL
        action = strategy.decide(
            open_price=101.0, close_price=101.0,
            shares=100, date=self.df.iloc[1]["date"],
        )
        self.assertEqual(action, "sell")

    def test_no_sell_when_no_shares(self):
        """当日上涨但无持仓时，不应输出 sell（不卖空）。"""
        strategy = CloseReversalDecision(df=self.df)
        action = strategy.decide(
            open_price=101.0, close_price=101.0,
            shares=0, date=self.df.iloc[1]["date"],
        )
        self.assertIsNone(action)

    def test_no_signal_when_price_unchanged(self):
        """收盘价相同时，应返回 None（持平无操作）。"""
        flat_df = pd.DataFrame({
            "date": pd.date_range(start="2023-01-01", periods=2, freq="D"),
            "open": [100.0, 100.0],
            "high": [101.0, 101.0],
            "low": [99.0, 99.0],
            "close": [100.0, 100.0],
            "volume": [1000, 1000],
        })
        strategy = CloseReversalDecision(df=flat_df)
        action = strategy.decide(
            open_price=100.0, close_price=100.0,
            shares=100, date=flat_df.iloc[1]["date"],
        )
        self.assertIsNone(action)

    def test_no_signal_within_min_change_threshold(self):
        """当涨跌幅在 min_change_pct 阈值内时，应返回 None。"""
        dates = pd.date_range(start="2023-01-01", periods=2, freq="D")
        df = pd.DataFrame({
            "date": dates,
            "open": [100.0, 100.5],
            "high": [101.0, 101.0],
            "low": [99.0, 99.5],
            "close": [100.0, 100.5],
            "volume": [1000, 1000],
        })
        # 涨幅为 0.5%，设置 min_change_pct=1.0%，应被过滤
        strategy = CloseReversalDecision(min_change_pct=1.0, df=df)
        action = strategy.decide(
            open_price=100.5, close_price=100.5,
            shares=100, date=df.iloc[1]["date"],
        )
        self.assertIsNone(action)

    def test_sell_signal_exceeds_min_change_threshold(self):
        """当涨幅超过 min_change_pct 阈值且有持仓时，应输出 sell。"""
        dates = pd.date_range(start="2023-01-01", periods=2, freq="D")
        df = pd.DataFrame({
            "date": dates,
            "open": [100.0, 102.0],
            "high": [101.0, 103.0],
            "low": [99.0, 101.0],
            "close": [100.0, 102.0],
            "volume": [1000, 1000],
        })
        # 涨幅 2%，设置 min_change_pct=1.0%，应触发卖出
        strategy = CloseReversalDecision(min_change_pct=1.0, df=df)
        action = strategy.decide(
            open_price=102.0, close_price=102.0,
            shares=100, date=df.iloc[1]["date"],
        )
        self.assertEqual(action, "sell")

    def test_return_none_when_no_df(self):
        """当没有设置 df 时，应返回 None。"""
        strategy = CloseReversalDecision()
        action = strategy.decide(
            open_price=100.0, close_price=100.0,
            shares=0, date="2023-01-01",
        )
        self.assertIsNone(action)

    def test_return_none_on_first_day(self):
        """第一日没有前一日数据，应返回 None。"""
        strategy = CloseReversalDecision(df=self.df)
        action = strategy.decide(
            open_price=100.0, close_price=100.0,
            shares=0, date=self.df.iloc[0]["date"],
        )
        self.assertIsNone(action)


class TestCloseReversalCreateStrategy(unittest.TestCase):
    """create_strategy 工厂函数测试。"""

    def test_create_strategy_returns_instance(self):
        dates = pd.date_range(start="2023-01-01", periods=3, freq="D")
        df = pd.DataFrame({
            "date": dates,
            "open": [100.0, 101.0, 99.0],
            "high": [101.0, 102.0, 100.0],
            "low": [99.0, 100.0, 98.0],
            "close": [100.0, 101.0, 99.0],
            "volume": [1000, 1000, 1000],
        })
        strategy = create_strategy(df=df)
        self.assertIsInstance(strategy, CloseReversalDecision)
        self.assertEqual(strategy.min_change_pct, 0.0)

    def test_create_strategy_with_params(self):
        dates = pd.date_range(start="2023-01-01", periods=3, freq="D")
        df = pd.DataFrame({
            "date": dates,
            "open": [100.0, 101.0, 99.0],
            "high": [101.0, 102.0, 100.0],
            "low": [99.0, 100.0, 98.0],
            "close": [100.0, 101.0, 99.0],
            "volume": [1000, 1000, 1000],
        })
        strategy = create_strategy(df=df, min_change_pct=0.5)
        self.assertEqual(strategy.min_change_pct, 0.5)


class TestCloseReversalPrepareBacktestData(unittest.TestCase):
    """prepare_backtest_data 函数测试。"""

    def test_returns_copy_of_input(self):
        dates = pd.date_range(start="2023-01-01", periods=3, freq="D")
        df = pd.DataFrame({
            "date": dates,
            "open": [100.0, 101.0, 99.0],
            "high": [101.0, 102.0, 100.0],
            "low": [99.0, 100.0, 98.0],
            "close": [100.0, 101.0, 99.0],
            "volume": [1000, 1000, 1000],
        })
        result = prepare_backtest_data(df)
        self.assertIsNot(result, df)  # 应为副本
        pd.testing.assert_frame_equal(result, df)


class TestCloseReversalValidateParameters(unittest.TestCase):
    """参数校验测试。"""

    def test_valid_parameters(self):
        # 正常参数不应抛出异常
        validate_strategy_parameters(min_change_pct=0.0)
        validate_strategy_parameters(min_change_pct=0.5)

    def test_negative_min_change_pct_raises(self):
        with self.assertRaises(ValueError):
            validate_strategy_parameters(min_change_pct=-1.0)

    def test_valid_fund_types(self):
        """合法的基金类型不应抛出异常。"""
        validate_strategy_parameters(fund_type='on_exchange')
        validate_strategy_parameters(fund_type='off_exchange')

    def test_invalid_fund_type_raises(self):
        """非法的基金类型应抛出异常。"""
        with self.assertRaises(ValueError):
            validate_strategy_parameters(fund_type='invalid_type')

    def test_invalid_fund_type_raises_with_default_message(self):
        """非法基金类型的错误信息应包含支持的类型。"""
        with self.assertRaisesRegex(ValueError, "on_exchange|off_exchange"):
            validate_strategy_parameters(fund_type='unknown')


if __name__ == "__main__":
    unittest.main()
