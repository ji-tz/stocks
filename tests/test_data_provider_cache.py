import os
import tempfile
import pandas as pd
import unittest
from unittest.mock import patch

from exchange.source.data_provider import get_data


class TestDataProviderCacheFiltering(unittest.TestCase):
    def test_cache_filtered_by_date_range(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_file = os.path.join(tmp, '600900.csv')
            dates = pd.date_range(start='2023-01-01', periods=10, freq='D')
            df = pd.DataFrame({
                'date': dates,
                'open': [100+i for i in range(10)],
                'high': [101+i for i in range(10)],
                'low': [99+i for i in range(10)],
                'close': [100+i for i in range(10)],
                'volume': [1000+i*10 for i in range(10)],
            })
            df.to_csv(cache_file, index=False)

            out = get_data(symbol='600900', source='akshare', start_date='20230103', end_date='20230105', cache_dir=tmp)
            self.assertEqual(out['date'].min().strftime('%Y-%m-%d'), '2023-01-03')
            self.assertEqual(out['date'].max().strftime('%Y-%m-%d'), '2023-01-05')

    @patch('exchange.source.data_provider.AkshareProvider.fetch')
    def test_force_refresh_fetches_even_when_cache_exists(self, mock_fetch):
        with tempfile.TemporaryDirectory() as tmp:
            cache_file = os.path.join(tmp, '600900.csv')
            cached_df = pd.DataFrame({
                'date': pd.date_range(start='2023-01-01', periods=5, freq='D'),
                'open': [10, 11, 12, 13, 14],
                'high': [11, 12, 13, 14, 15],
                'low': [9, 10, 11, 12, 13],
                'close': [10, 11, 12, 13, 14],
                'volume': [100] * 5,
            })
            cached_df.to_csv(cache_file, index=False)

            refreshed_df = pd.DataFrame({
                'date': pd.date_range(start='2023-01-01', periods=5, freq='D'),
                'open': [20, 21, 22, 23, 24],
                'high': [21, 22, 23, 24, 25],
                'low': [19, 20, 21, 22, 23],
                'close': [20, 21, 22, 23, 24],
                'volume': [200] * 5,
            })
            mock_fetch.return_value = refreshed_df

            out = get_data(symbol='600900', source='akshare', cache_dir=tmp, force_refresh=True)
            self.assertEqual(mock_fetch.call_count, 1)
            self.assertEqual(float(out.iloc[0]['open']), 20.0)

    @patch('exchange.source.data_provider.AkshareProvider.fetch')
    def test_fetch_uses_buffer_days_but_returns_requested_range(self, mock_fetch):
        with tempfile.TemporaryDirectory() as tmp:
            mock_fetch.return_value = pd.DataFrame({
                'date': pd.to_datetime(['2022-12-29', '2023-01-01', '2023-01-03', '2023-01-05', '2023-01-08']),
                'open': [9, 10, 11, 12, 13],
                'high': [10, 11, 12, 13, 14],
                'low': [8, 9, 10, 11, 12],
                'close': [9, 10, 11, 12, 13],
                'volume': [100] * 5,
            })

            out = get_data(
                symbol='600900',
                source='akshare',
                start_date='20230103',
                end_date='20230105',
                cache_dir=tmp,
                buffer_days=5,
            )

            self.assertEqual(mock_fetch.call_args.kwargs['start_date'], '20221229')
            self.assertEqual(mock_fetch.call_args.kwargs['end_date'], '20230110')
            self.assertEqual(out['date'].min().strftime('%Y-%m-%d'), '2023-01-03')
            self.assertEqual(out['date'].max().strftime('%Y-%m-%d'), '2023-01-05')


if __name__ == '__main__':
    unittest.main()
