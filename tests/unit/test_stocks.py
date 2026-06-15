import os
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

import trader.stocks as stocks


def make_mock_df(n=10):
    dates = pd.date_range(end="2023-12-31", periods=n, freq="D")
    data = {
        "date": dates,
        "open": [100.0 + i for i in range(n)],
        "high": [101.0 + i for i in range(n)],
        "low": [99.0 + i for i in range(n)],
        "close": [100.0 + i for i in range(n)],
        "volume": [1000 + i * 10 for i in range(n)],
    }
    return pd.DataFrame(data)


class TestStocksModule(unittest.TestCase):
    def test_init_creates_cache_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = os.path.join(tmp, "cache_here")
            # ensure not exists
            if os.path.exists(cache_dir):
                os.rmdir(cache_dir)
            stocks.init(cache_dir=cache_dir)
            self.assertTrue(os.path.isdir(cache_dir))

    @patch('trader.stocks._get_data')
    def test_get_data_wrapper(self, mock_get):
        df = make_mock_df(5)
        mock_get.return_value = df
        out = stocks.get_data(symbol='600900', source='auto')
        # should return the same dataframe object
        self.assertIs(out, df)
        self.assertListEqual(list(out.columns), ['date', 'open', 'high', 'low', 'close', 'volume'])

    def test_get_data_invalid_date_raises(self):
        # ensure invalid date string raises and underlying provider is not called
        with self.assertRaises(ValueError):
            stocks.get_data(symbol='600900', source='auto', start_date='202301')

    @patch('trader.stocks._get_data')
    def test_get_data_normalizes_hyphen_for_akshare_auto(self, mock_get):
        # when source is auto and start_date provided as YYYY-MM-DD, we expect underlying get_data to receive YYYYMMDD
        mock_get.return_value = make_mock_df(3)
        stocks.get_data(symbol='600900', source='auto', start_date='2023-01-01', end_date='2023-01-03')
        # verify call used normalized YYYYMMDD for start_date
        called_kwargs = mock_get.call_args.kwargs
        self.assertEqual(called_kwargs.get('start_date'), '20230101')
        self.assertEqual(called_kwargs.get('end_date'), '20230103')

    @patch('trader.stocks._get_data')
    def test_get_data_passes_force_refresh_and_buffer_days(self, mock_get):
        mock_get.return_value = make_mock_df(3)
        stocks.get_data(
            symbol='600900', source='auto', start_date='20230101', end_date='20230103',
            force_refresh=True, buffer_days=7,
        )
        called_kwargs = mock_get.call_args.kwargs
        self.assertTrue(called_kwargs.get('force_refresh'))
        self.assertEqual(called_kwargs.get('buffer_days'), 7)

    @patch('trader.stocks._get_data')
    def test_get_data_filters_returned_df_by_date(self, mock_get):
        # Create a dataframe spanning several dates
        dates = pd.date_range(start='2023-01-01', periods=10, freq='D')
        df = pd.DataFrame({
            'date': dates,
            'open': [100+i for i in range(10)],
            'high': [101+i for i in range(10)],
            'low': [99+i for i in range(10)],
            'close': [100+i for i in range(10)],
            'volume': [1000+i*10 for i in range(10)],
        })
        mock_get.return_value = df

        out = stocks.get_data(symbol='600900', source='auto', start_date='20230103', end_date='20230105')
        # should be filtered to include only dates 2023-01-03 .. 2023-01-05
        self.assertEqual(out['date'].min().strftime('%Y-%m-%d'), '2023-01-03')
        self.assertEqual(out['date'].max().strftime('%Y-%m-%d'), '2023-01-05')

    @patch('trader.simulator.get_data')
    def test_run_mean_cost_returns_expected_keys(self, mock_get):
        # simulate_mean_cost 在 simulator.simulator 模块内绑定了 get_data，需在该引用处打补丁
        mock_get.return_value = make_mock_df(8)
        res = stocks.run_mean_cost(symbol='600900', start_date='20230101', end_date='20231231', lot_size=1, init_cash=10000.0, source='auto')
        # check some expected keys exist and types
        self.assertIn('symbol', res)
        self.assertIn('init_cash', res)
        self.assertIn('total_value', res)
        self.assertIsInstance(res['init_cash'], float)
        self.assertIsInstance(res['total_value'], float)

    def test_list_strategy_specs_contains_registered_parameters(self):
        specs = {spec.key: spec for spec in stocks.list_strategy_specs()}

        self.assertIn('sma', specs)
        self.assertIn('mean_cost', specs)
        self.assertIn('fixed_amount', specs)
        self.assertIn('dual_ma', specs)
        self.assertIn('bollinger', specs)
        self.assertIn('rsi', specs)
        self.assertIn('a50_prev_night_1h', specs)
        self.assertIn('signal_template', specs)
        self.assertEqual(specs['sma'].parameters[0].name, 'period')
        self.assertEqual(specs['fixed_amount'].parameters[0].name, 'fixed_amount')
        self.assertEqual(specs['dual_ma'].parameters[0].name, 'short_period')
        self.assertEqual(specs['bollinger'].parameters[1].name, 'std_multiplier')
        self.assertEqual(specs['rsi'].parameters[2].name, 'overbought')
        self.assertEqual(specs['a50_prev_night_1h'].parameters[0].name, 'futures_symbol')
        self.assertEqual(specs['signal_template'].parameters[0].name, 'buy_trigger')
        self.assertEqual(specs['mean_cost'].supported_trade_prices, (stocks.TRADE_PRICE_OPEN,))

    @patch('trader.stocks.run_fixed_amount')
    def test_run_backtest_dispatches_strategy_registry(self, mock_run_fixed_amount):
        mock_run_fixed_amount.return_value = {'symbol': '600900', 'total_value': 101000.0}

        request = stocks.create_backtest_request(
            symbol='600900',
            strategy='fixed_amount',
            source='auto',
            start_date='20230101',
            end_date='20231231',
            lot_size=100,
            init_cash=100000.0,
            strategy_params={'fixed_amount': '2000'},
        )
        result = stocks.run_backtest(request)

        self.assertEqual(result['symbol'], '600900')
        mock_run_fixed_amount.assert_called_once_with(
            symbol='600900',
            start_date='20230101',
            end_date='20231231',
            lot_size=100,
            init_cash=100000.0,
            source='auto',
            progress_callback=None,
            trade_price='open',
            fixed_amount=2000.0,
        )

    def test_create_backtest_request_rejects_unsupported_trade_price(self):
        with self.assertRaises(ValueError):
            stocks.create_backtest_request(strategy='sma', trade_price='close')

    @patch('trader.stocks.run_sma_backtest')
    def test_run_backtest_dispatches_sma_period(self, mock_run_sma_backtest):
        mock_run_sma_backtest.return_value = {'symbol': '600900', 'total_value': 102000.0}

        request = stocks.create_backtest_request(
            symbol='600900',
            strategy='sma',
            source='auto',
            start_date='20230101',
            end_date='20231231',
            lot_size=100,
            init_cash=100000.0,
            strategy_params={'period': '15'},
        )
        result = stocks.run_backtest(request)

        self.assertEqual(result['symbol'], '600900')
        mock_run_sma_backtest.assert_called_once_with(
            symbol='600900',
            start_date='20230101',
            end_date='20231231',
            lot_size=100,
            init_cash=100000.0,
            source='auto',
            progress_callback=None,
            trade_price='open',
            period=15,
        )

    @patch('trader.stocks.run_futures_a50_prev_night')
    def test_run_backtest_dispatches_a50_strategy(self, mock_run_a50):
        mock_run_a50.return_value = {'symbol': '600900', 'total_value': 103000.0}

        request = stocks.create_backtest_request(
            symbol='600900',
            strategy='a50_prev_night_1h',
            source='auto',
            start_date='20230101',
            end_date='20231231',
            lot_size=100,
            init_cash=100000.0,
            strategy_params={'futures_symbol': 'FTSE_A50', 'base_position_lots': '2'},
        )
        result = stocks.run_backtest(request)

        self.assertEqual(result['symbol'], '600900')
        mock_run_a50.assert_called_once_with(
            symbol='600900',
            start_date='20230101',
            end_date='20231231',
            lot_size=100,
            init_cash=100000.0,
            source='auto',
            progress_callback=None,
            trade_price='open',
            futures_symbol='FTSE_A50',
            base_position_lots=2,
        )

    @patch('trader.stocks.run_signal_template')
    def test_run_backtest_dispatches_signal_template_strategy(self, mock_run_signal_template):
        mock_run_signal_template.return_value = {'symbol': '600900', 'total_value': 104000.0}

        request = stocks.create_backtest_request(
            symbol='600900',
            strategy='signal_template',
            source='auto',
            start_date='20230101',
            end_date='20231231',
            lot_size=100,
            init_cash=100000.0,
            trade_price='close',
            strategy_params={
                'buy_trigger': 'macd_golden',
                'buy_exec_mode': 'fixed_amount',
                'buy_fixed_amount': '20000',
                'sell_trigger': 'profit_target',
                'sell_profit_pct': '8',
                'sell_exec_mode': 'ratio',
                'sell_ratio_pct': '50',
            },
        )
        result = stocks.run_backtest(request)

        self.assertEqual(result['symbol'], '600900')
        mock_run_signal_template.assert_called_once_with(
            symbol='600900',
            start_date='20230101',
            end_date='20231231',
            lot_size=100,
            init_cash=100000.0,
            source='auto',
            progress_callback=None,
            trade_price='close',
            buy_trigger='macd_golden',
            buy_price_value=0.0,
            buy_exec_mode='fixed_amount',
            buy_fixed_amount=20000.0,
            buy_position_pct=30.0,
            take_profit_pct=0.0,
            stop_loss_pct=0.0,
            sell_trigger='profit_target',
            sell_price_value=0.0,
            sell_profit_pct=8.0,
            sell_loss_pct=0.0,
            sell_exec_mode='ratio',
            sell_fixed_shares=100.0,
            sell_ratio_pct=50.0,
        )


if __name__ == '__main__':
    unittest.main()
