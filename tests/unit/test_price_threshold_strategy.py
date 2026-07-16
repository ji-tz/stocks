"""单元测试：价格阈值策略（Price Threshold Strategy）

测试用例覆盖：
1. 价格低于买入阈值 → BUY 信号
2. 价格高于卖出阈值 → SELL 信号
3. 价格在阈值之间 → 无信号（None）
4. 价格等于阈值时不触发（严格比较）
5. close_price 为 None 时返回 None
6. date 为 None 时不执行
7. 时间过滤：日线 bar（无时间）视为匹配
8. 时间过滤：分钟线恰好匹配决策时间 → 触发
9. 时间过滤：分钟线不匹配时间 → 跳过
10. create_strategy 工厂函数
11. prepare_backtest_data 返回副本
12. 参数校验：非法参数抛出异常
"""
import unittest

import pandas as pd

from strategy.price_threshold_strategy import (
    PriceThresholdDecision,
    create_strategy,
    prepare_backtest_data,
    prepare_backtest_data_for_tick,
    validate_strategy_parameters,
)


class TestPriceThresholdDecision(unittest.TestCase):
    """策略决策器的核心信号测试。"""

    def setUp(self):
        """标准测试数据集：价格在 8~12 之间波动。"""
        dates = pd.date_range(start="2023-01-01", periods=4, freq="D")
        self.df = pd.DataFrame({
            "date": dates,
            "open": [10.0, 7.0, 13.0, 10.0],
            "high": [11.0, 8.0, 14.0, 11.0],
            "low": [9.0, 6.0, 12.0, 9.0],
            "close": [10.0, 7.0, 13.0, 10.0],
            "volume": [1000, 1000, 1000, 1000],
        })

    def test_buy_signal_when_price_below_threshold(self):
        """当价格低于买入阈值时，应返回 buy 信号。"""
        strategy = PriceThresholdDecision(buy_threshold=8.0, sell_threshold=12.0, df=self.df)
        action = strategy.decide(
            open_price=7.0, close_price=7.0,
            shares=0, date=self.df.iloc[1]["date"],
        )
        self.assertEqual(action, "buy")

    def test_sell_signal_when_price_above_threshold(self):
        """当价格高于卖出阈值时，应返回 sell 信号。"""
        strategy = PriceThresholdDecision(buy_threshold=8.0, sell_threshold=12.0, df=self.df)
        action = strategy.decide(
            open_price=13.0, close_price=13.0,
            shares=100, date=self.df.iloc[2]["date"],
        )
        self.assertEqual(action, "sell")

    def test_no_signal_in_hold_zone(self):
        """当价格在买入阈值和卖出阈值之间时，应返回 None。"""
        strategy = PriceThresholdDecision(buy_threshold=8.0, sell_threshold=12.0, df=self.df)
        action = strategy.decide(
            open_price=10.0, close_price=10.0,
            shares=0, date=self.df.iloc[0]["date"],
        )
        self.assertIsNone(action)

    def test_buy_precedence_when_thresholds_overlap(self):
        """当 buy_threshold > sell_threshold 导致重叠时，buy 优先。"""
        strategy = PriceThresholdDecision(buy_threshold=10.0, sell_threshold=5.0, df=self.df)
        action = strategy.decide(
            open_price=7.0, close_price=7.0,
            shares=0, date=self.df.iloc[1]["date"],
        )
        self.assertEqual(action, "buy")

    def test_no_signal_when_price_equals_buy_threshold(self):
        """当价格等于买入阈值时，不触发（严格小于才触发）。"""
        strategy = PriceThresholdDecision(buy_threshold=10.0, sell_threshold=12.0, df=self.df)
        action = strategy.decide(
            open_price=10.0, close_price=10.0,
            shares=0, date=self.df.iloc[0]["date"],
        )
        self.assertIsNone(action)

    def test_no_signal_when_price_equals_sell_threshold(self):
        """当价格等于卖出阈值时，不触发（严格大于才触发）。"""
        strategy = PriceThresholdDecision(buy_threshold=8.0, sell_threshold=10.0, df=self.df)
        action = strategy.decide(
            open_price=10.0, close_price=10.0,
            shares=0, date=self.df.iloc[0]["date"],
        )
        self.assertIsNone(action)

    def test_return_none_when_no_close_price(self):
        """当 close_price 为 None 时返回 None。"""
        strategy = PriceThresholdDecision(df=self.df)
        action = strategy.decide(
            open_price=10.0, close_price=None,
            shares=0, date="2023-01-01",
        )
        self.assertIsNone(action)

    def test_return_none_when_date_is_none(self):
        """date 为 None 时不执行决策。"""
        strategy = PriceThresholdDecision(buy_threshold=8.0, sell_threshold=12.0)
        action = strategy.decide(
            open_price=7.0, close_price=7.0,
            shares=0, date=None,
        )
        self.assertIsNone(action)


class TestPriceThresholdTimeFilter(unittest.TestCase):
    """时间过滤逻辑测试。"""

    def test_matches_daily_bar_without_time(self):
        """日线 bar（仅日期，hour=0, minute=0）应视为时间匹配。"""
        strategy = PriceThresholdDecision(
            buy_threshold=8.0, sell_threshold=12.0)
        action = strategy.decide(
            open_price=7.0, close_price=7.0,
            shares=0, date=pd.Timestamp("2023-01-01"),
        )
        self.assertEqual(action, "buy")

    def test_matches_minute_bar_at_decision_time(self):
        """分钟线 bar 恰好匹配决策时间 (10:00) 时触发。"""
        strategy = PriceThresholdDecision(
            buy_threshold=8.0, sell_threshold=12.0,
            decision_hour=10, decision_minute=0,
        )
        action = strategy.decide(
            open_price=7.0, close_price=7.0,
            shares=0, date=pd.Timestamp("2023-01-01 10:00"),
        )
        self.assertEqual(action, "buy")

    def test_skips_minute_bar_wrong_time(self):
        """分钟线 bar 不匹配决策时间 (10:00) 时返回 None。"""
        strategy = PriceThresholdDecision(
            buy_threshold=8.0, sell_threshold=12.0,
            decision_hour=10, decision_minute=0,
        )
        action = strategy.decide(
            open_price=7.0, close_price=7.0,
            shares=0, date=pd.Timestamp("2023-01-01 14:30"),
        )
        self.assertIsNone(action)

    def test_skips_minute_bar_wrong_minute(self):
        """分钟线 bar 小时匹配但分钟不匹配时返回 None。"""
        strategy = PriceThresholdDecision(
            buy_threshold=8.0, sell_threshold=12.0,
            decision_hour=10, decision_minute=0,
        )
        action = strategy.decide(
            open_price=7.0, close_price=7.0,
            shares=0, date=pd.Timestamp("2023-01-01 10:05"),
        )
        self.assertIsNone(action)

    def test_matches_custom_decision_time(self):
        """自定义决策时间 14:58 应正确匹配。"""
        strategy = PriceThresholdDecision(
            buy_threshold=8.0, sell_threshold=12.0,
            decision_hour=14, decision_minute=58,
        )
        action = strategy.decide(
            open_price=7.0, close_price=7.0,
            shares=0, date=pd.Timestamp("2023-01-01 14:58"),
        )
        self.assertEqual(action, "buy")

    def test_matches_datetime_string_with_time(self):
        """字符串格式的 datetime 应正确解析并匹配时间。"""
        strategy = PriceThresholdDecision(
            buy_threshold=8.0, sell_threshold=12.0,
            decision_hour=14, decision_minute=30,
        )
        action = strategy.decide(
            open_price=7.0, close_price=7.0,
            shares=0, date="2023-01-01 14:30:00",
        )
        self.assertEqual(action, "buy")


class TestPriceThresholdCreateStrategy(unittest.TestCase):
    """create_strategy 工厂函数测试。"""

    def test_create_strategy_returns_instance(self):
        df = pd.DataFrame({
            "date": pd.date_range(start="2023-01-01", periods=3, freq="D"),
            "open": [10.0, 10.0, 10.0],
            "high": [11.0, 11.0, 11.0],
            "low": [9.0, 9.0, 9.0],
            "close": [10.0, 10.0, 10.0],
            "volume": [1000, 1000, 1000],
        })
        strategy = create_strategy(df=df)
        self.assertIsInstance(strategy, PriceThresholdDecision)
        self.assertEqual(strategy.buy_threshold, 8.0)
        self.assertEqual(strategy.sell_threshold, 12.0)
        self.assertEqual(strategy.decision_hour, 10)
        self.assertEqual(strategy.decision_minute, 0)

    def test_create_strategy_with_custom_params(self):
        df = pd.DataFrame({
            "date": pd.date_range(start="2023-01-01", periods=3, freq="D"),
            "open": [10.0, 10.0, 10.0],
            "high": [11.0, 11.0, 11.0],
            "low": [9.0, 9.0, 9.0],
            "close": [10.0, 10.0, 10.0],
            "volume": [1000, 1000, 1000],
        })
        strategy = create_strategy(
            df=df,
            buy_threshold=5.0,
            sell_threshold=15.0,
            decision_hour=14,
            decision_minute=30,
        )
        self.assertEqual(strategy.buy_threshold, 5.0)
        self.assertEqual(strategy.sell_threshold, 15.0)
        self.assertEqual(strategy.decision_hour, 14)
        self.assertEqual(strategy.decision_minute, 30)


class TestPriceThresholdPrepareBacktestData(unittest.TestCase):
    """prepare_backtest_data 函数测试。"""

    def test_returns_copy_of_input(self):
        dates = pd.date_range(start="2023-01-01", periods=3, freq="D")
        df = pd.DataFrame({
            "date": dates,
            "open": [10.0, 10.0, 10.0],
            "high": [11.0, 11.0, 11.0],
            "low": [9.0, 9.0, 9.0],
            "close": [10.0, 10.0, 10.0],
            "volume": [1000, 1000, 1000],
        })
        result = prepare_backtest_data(df)
        self.assertIsNot(result, df)
        pd.testing.assert_frame_equal(result, df)

    def test_prepare_backtest_data_for_tick_returns_copy(self):
        df = pd.DataFrame({
            "date": pd.date_range(start="2023-01-01", periods=3, freq="D"),
            "close": [10.0, 10.0, 10.0],
        })
        result = prepare_backtest_data_for_tick(df)
        self.assertIsNot(result, df)
        pd.testing.assert_frame_equal(result, df)


class TestPriceThresholdValidateParameters(unittest.TestCase):
    """参数校验测试。"""

    def test_valid_parameters(self):
        """合法参数不应抛出异常。"""
        validate_strategy_parameters(buy_threshold=5.0, sell_threshold=15.0)
        validate_strategy_parameters(buy_threshold=0.1, sell_threshold=100.0)
        validate_strategy_parameters(
            buy_threshold=5.0, sell_threshold=15.0,
            decision_hour=0, decision_minute=0,
        )
        validate_strategy_parameters(
            buy_threshold=5.0, sell_threshold=15.0,
            decision_hour=23, decision_minute=59,
        )

    def test_buy_threshold_zero_raises(self):
        with self.assertRaises(ValueError):
            validate_strategy_parameters(buy_threshold=0)

    def test_buy_threshold_negative_raises(self):
        with self.assertRaises(ValueError):
            validate_strategy_parameters(buy_threshold=-1.0)

    def test_sell_threshold_zero_raises(self):
        with self.assertRaises(ValueError):
            validate_strategy_parameters(sell_threshold=0)

    def test_sell_threshold_negative_raises(self):
        with self.assertRaises(ValueError):
            validate_strategy_parameters(sell_threshold=-5.0)

    def test_decision_hour_too_low_raises(self):
        with self.assertRaises(ValueError):
            validate_strategy_parameters(decision_hour=-1)

    def test_decision_hour_too_high_raises(self):
        with self.assertRaises(ValueError):
            validate_strategy_parameters(decision_hour=24)

    def test_decision_minute_too_low_raises(self):
        with self.assertRaises(ValueError):
            validate_strategy_parameters(decision_minute=-1)

    def test_decision_minute_too_high_raises(self):
        with self.assertRaises(ValueError):
            validate_strategy_parameters(decision_minute=60)


if __name__ == "__main__":
    unittest.main()
