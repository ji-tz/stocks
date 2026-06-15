import unittest

import pandas as pd

from trader.simulator import Simulator
from strategy.futures_open_hour_strategy import FuturesOpenHourDecision


class TestFuturesOpenHourStrategy(unittest.TestCase):
    def make_stock_hourly_df(self):
        dates = pd.date_range(start="2023-01-03 09:30:00", periods=4, freq="h")
        prices = [10.0, 10.1, 10.2, 10.3]
        return pd.DataFrame(
            {
                "date": dates,
                "open": prices,
                "high": [p + 0.1 for p in prices],
                "low": [p - 0.1 for p in prices],
                "close": [p + 0.02 for p in prices],
                "volume": [1000] * len(prices),
            }
        )

    def make_futures_daily_df(self, up: bool = True):
        closes = [100.0, 101.0] if up else [101.0, 100.0]
        return pd.DataFrame(
            {
                "date": pd.to_datetime(["2023-01-01", "2023-01-02"]),
                "open": closes,
                "high": [c + 1 for c in closes],
                "low": [c - 1 for c in closes],
                "close": closes,
                "volume": [1000, 1000],
            }
        )

    def test_buy_and_sell_after_one_hour_when_prev_night_up(self):
        stock_df = self.make_stock_hourly_df()
        futures_df = self.make_futures_daily_df(up=True)

        strategy = FuturesOpenHourDecision(futures_df=futures_df)
        sim = Simulator(lot_size=100, init_cash=100000.0)

        result = sim.simulate(
            df=stock_df,
            strategy=strategy,
            symbol="TEST",
            granularity="1h",
            enable_scheduled_orders=True,
            enforce_t_plus_one=False,
        )

        self.assertEqual(result["trades"], 2)
        self.assertEqual(result["trades_list"][0]["action"], "buy")
        self.assertEqual(result["trades_list"][1]["action"], "sell")
        self.assertIn("scheduled", result["trades_list"][1]["source"])

    def test_no_buy_when_prev_night_down(self):
        stock_df = self.make_stock_hourly_df()
        futures_df = self.make_futures_daily_df(up=False)

        strategy = FuturesOpenHourDecision(futures_df=futures_df)
        sim = Simulator(lot_size=100, init_cash=100000.0)

        result = sim.simulate(
            df=stock_df,
            strategy=strategy,
            symbol="TEST",
            granularity="1h",
            enable_scheduled_orders=True,
            enforce_t_plus_one=False,
        )

        self.assertEqual(result["trades"], 0)
        self.assertEqual(len(result["trades_list"]), 0)

    def test_buy_and_sell_with_base_position_when_prev_night_up(self):
        stock_df = self.make_stock_hourly_df()
        futures_df = self.make_futures_daily_df(up=True)

        strategy = FuturesOpenHourDecision(futures_df=futures_df)
        sim = Simulator(lot_size=100, init_cash=100000.0)

        result = sim.simulate(
            df=stock_df,
            strategy=strategy,
            symbol="TEST",
            granularity="1h",
            enable_scheduled_orders=True,
            enforce_t_plus_one=True,
            require_base_position_for_t_plus_one_intraday=True,
            base_position_lots=2,
        )

        self.assertEqual(result["base_position_lots"], 2)
        self.assertEqual(result["trades"], 2)
        self.assertEqual(result["trades_list"][0]["action"], "buy")
        self.assertEqual(result["trades_list"][1]["action"], "sell")
        self.assertEqual(result["trades_list"][0]["shares"], 100.0)
        self.assertEqual(result["trades_list"][1]["shares"], 100.0)
        self.assertEqual(result["shares"], 200.0)


if __name__ == "__main__":
    unittest.main()
