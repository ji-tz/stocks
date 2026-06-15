import unittest
from unittest.mock import patch
from types import SimpleNamespace

import pandas as pd

import trader.stocks as stocks
from strategy.bollinger_strategy import BollingerDecision
from strategy.dual_ma_strategy import DualMaDecision
from strategy.rsi_strategy import RsiDecision


def make_test_df(prices):
    dates = pd.date_range(start="2023-01-01", periods=len(prices), freq="D")
    return pd.DataFrame({
        "date": dates,
        "open": prices,
        # 保留完整 OHLCV 结构，确保与真实回测数据格式一致。
        "high": [price + 0.5 for price in prices],
        "low": [price - 0.5 for price in prices],
        "close": prices,
        "volume": [1000] * len(prices),
    })


class TestDualMaDecision(unittest.TestCase):
    def test_golden_cross_buy_signal(self):
        dates = pd.date_range(start="2023-01-01", periods=3, freq="D")
        df = pd.DataFrame({
            "date": dates,
            "ma_short": [9.0, 10.0, 12.0],
            "ma_long": [10.0, 10.0, 11.0],
        })
        strategy = DualMaDecision(short_period=2, long_period=3, df=df)
        action = strategy.decide(open_price=11.0, close_price=11.0, shares=0, date=dates[-1])
        self.assertEqual(action, "buy")

    def test_death_cross_sell_signal(self):
        dates = pd.date_range(start="2023-01-01", periods=3, freq="D")
        df = pd.DataFrame({
            "date": dates,
            "ma_short": [12.0, 11.0, 9.0],
            "ma_long": [11.0, 11.0, 10.0],
        })
        strategy = DualMaDecision(short_period=2, long_period=3, df=df)
        action = strategy.decide(open_price=9.0, close_price=9.0, shares=100, date=dates[-1])
        self.assertEqual(action, "sell")


class TestBollingerDecision(unittest.TestCase):
    def test_buy_below_lower_band(self):
        dates = pd.date_range(start="2023-01-01", periods=1, freq="D")
        df = pd.DataFrame({
            "date": dates,
            "bollinger_upper": [11.0],
            "bollinger_lower": [9.0],
        })
        strategy = BollingerDecision(period=20, std_multiplier=2.0, df=df)
        action = strategy.decide(open_price=8.5, close_price=8.5, shares=0, date=dates[0])
        self.assertEqual(action, "buy")

    def test_sell_above_upper_band(self):
        dates = pd.date_range(start="2023-01-01", periods=1, freq="D")
        df = pd.DataFrame({
            "date": dates,
            "bollinger_upper": [11.0],
            "bollinger_lower": [9.0],
        })
        strategy = BollingerDecision(period=20, std_multiplier=2.0, df=df)
        action = strategy.decide(open_price=11.5, close_price=11.5, shares=100, date=dates[0])
        self.assertEqual(action, "sell")


class TestRsiDecision(unittest.TestCase):
    def test_buy_when_rsi_is_oversold(self):
        dates = pd.date_range(start="2023-01-01", periods=1, freq="D")
        df = pd.DataFrame({"date": dates, "rsi": [25.0]})
        strategy = RsiDecision(period=14, oversold=30.0, overbought=70.0, df=df)
        action = strategy.decide(open_price=10.0, close_price=10.0, shares=0, date=dates[0])
        self.assertEqual(action, "buy")

    def test_sell_when_rsi_is_overbought(self):
        dates = pd.date_range(start="2023-01-01", periods=1, freq="D")
        df = pd.DataFrame({"date": dates, "rsi": [75.0]})
        strategy = RsiDecision(period=14, oversold=30.0, overbought=70.0, df=df)
        action = strategy.decide(open_price=10.0, close_price=10.0, shares=100, date=dates[0])
        self.assertEqual(action, "sell")


class TestLowFrequencyBacktests(unittest.TestCase):
    def test_generic_runner_rejects_empty_strategy_key(self):
        with self.assertRaises(ValueError):
            stocks.run_module_strategy_backtest(strategy_key='')

    def test_generic_runner_requires_create_strategy(self):
        with patch("trader.stocks.get_strategy_spec") as mock_get_strategy_spec, \
                patch("trader.stocks.importlib.import_module") as mock_import_module, \
                patch("trader.stocks._fetch_data_for_backtest") as mock_fetch_data:
            mock_get_strategy_spec.return_value = stocks.StrategySpec(
                key='dual_ma',
                label='双均线交叉',
                runner=stocks.run_module_strategy_backtest,
                module_name='strategy.dual_ma_strategy',
                module_interface=True,
            )
            mock_fetch_data.return_value = make_test_df([10, 11, 12])
            mock_import_module.return_value = SimpleNamespace()
            with self.assertRaises(RuntimeError):
                stocks.run_module_strategy_backtest(strategy_key='dual_ma')

    @patch("trader.stocks.run_module_strategy_backtest")
    def test_run_backtest_dispatches_generic_module_runner(self, mock_runner):
        mock_runner.return_value = {'symbol': '600900', 'total_value': 101000.0}
        request = stocks.create_backtest_request(
            symbol="600900",
            strategy="dual_ma",
            source="auto",
            start_date="20230101",
            end_date="20230113",
            lot_size=100,
            init_cash=100000.0,
            strategy_params={"short_period": "2", "long_period": "3"},
        )

        result = stocks.run_backtest(request)

        self.assertEqual(result["symbol"], "600900")
        mock_runner.assert_called_once_with(
            strategy_key='dual_ma',
            symbol='600900',
            start_date='20230101',
            end_date='20230113',
            lot_size=100.0,
            init_cash=100000.0,
            source='auto',
            progress_callback=None,
            trade_price='open',
            short_period=2,
            long_period=3,
        )

    @patch("trader.stocks._get_data")
    def test_run_backtest_supports_dual_ma(self, mock_get_data):
        mock_get_data.return_value = make_test_df([10, 9, 8, 9, 10, 11, 12, 11, 10, 9, 8, 9, 10])
        result = stocks.run_backtest(stocks.create_backtest_request(
            symbol="600900",
            strategy="dual_ma",
            source="auto",
            start_date="20230101",
            end_date="20230113",
            lot_size=100,
            init_cash=100000.0,
            strategy_params={"short_period": "2", "long_period": "3"},
        ))
        self.assertEqual(result["symbol"], "600900")
        self.assertIn("total_value", result)

    @patch("trader.stocks._get_data")
    def test_run_backtest_supports_bollinger(self, mock_get_data):
        mock_get_data.return_value = make_test_df([10, 10, 10, 10, 10, 6, 10, 10, 10, 14, 10, 10])
        result = stocks.run_backtest(stocks.create_backtest_request(
            symbol="600900",
            strategy="bollinger",
            source="auto",
            start_date="20230101",
            end_date="20230112",
            lot_size=100,
            init_cash=100000.0,
            strategy_params={"period": "5", "std_multiplier": "1.5"},
        ))
        self.assertEqual(result["symbol"], "600900")
        self.assertGreaterEqual(result["trades"], 1)

    @patch("trader.stocks._get_data")
    def test_run_backtest_supports_rsi(self, mock_get_data):
        mock_get_data.return_value = make_test_df([10, 9, 8, 7, 6, 7, 8, 9, 10, 11, 10, 9])
        result = stocks.run_backtest(stocks.create_backtest_request(
            symbol="600900",
            strategy="rsi",
            source="auto",
            start_date="20230101",
            end_date="20230112",
            lot_size=100,
            init_cash=100000.0,
            strategy_params={"period": "3", "oversold": "30", "overbought": "70"},
        ))
        self.assertEqual(result["symbol"], "600900")
        self.assertGreaterEqual(result["trades"], 1)

    def test_runner_parameter_validation(self):
        with self.assertRaises(ValueError):
            stocks.run_backtest(stocks.create_backtest_request(
                strategy='dual_ma',
                strategy_params={'short_period': '5', 'long_period': '5'},
            ))
        with self.assertRaises(ValueError):
            stocks.run_backtest(stocks.create_backtest_request(
                strategy='bollinger',
                strategy_params={'period': '20', 'std_multiplier': '0'},
            ))
        with self.assertRaises(ValueError):
            stocks.run_backtest(stocks.create_backtest_request(
                strategy='rsi',
                strategy_params={'period': '14', 'oversold': '80', 'overbought': '70'},
            ))


if __name__ == "__main__":
    unittest.main()
