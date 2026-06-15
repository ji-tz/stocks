import unittest
from unittest.mock import patch
import pandas as pd

import trader.stocks as stocks


class TestFuturesMissingData(unittest.TestCase):
    @patch('trader.stocks.get_data')
    def test_missing_futures_data_raises(self, mock_get):
        # 模拟股票数据可用但期货数据不可用的情况
        def _fake_get_data(symbol, source='auto', **kwargs):
            if symbol == 'FTSE_A50':
                return pd.DataFrame()
            dates = pd.date_range(end="2023-01-31", periods=5, freq='D')
            return pd.DataFrame({
                'date': dates,
                'open': [10.0 + i for i in range(5)],
                'high': [10.5 + i for i in range(5)],
                'low': [9.5 + i for i in range(5)],
                'close': [10.0 + i for i in range(5)],
                'volume': [1000 + i * 10 for i in range(5)],
            })

        mock_get.side_effect = _fake_get_data

        req = stocks.create_backtest_request(
            symbol='600900',
            strategy='a50_prev_night_1h',
            source='auto',
            start_date='20230101',
            end_date='20230131',
            lot_size=100.0,
            init_cash=100000.0,
            strategy_params={'futures_symbol': 'FTSE_A50'},
        )

        with self.assertRaises(RuntimeError) as cm:
            stocks.run_backtest(req)

        self.assertIn('无法获取期货数据', str(cm.exception))


if __name__ == '__main__':
    unittest.main()
