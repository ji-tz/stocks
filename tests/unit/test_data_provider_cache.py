import os
import tempfile
import pandas as pd
import unittest
from unittest.mock import patch

from exchange.source.data_provider import get_data, DEFAULT_FETCH_BUFFER_DAYS


class TestDataProviderCacheFiltering(unittest.TestCase):
    def test_default_buffer_days_is_one(self):
        """DEFAULT_FETCH_BUFFER_DAYS should be 1 to reduce overlap on partial fetches."""
        self.assertEqual(DEFAULT_FETCH_BUFFER_DAYS, 1)

    def test_cache_filtered_by_date_range(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_file = os.path.join(tmp, '600900.csv')
            dates = pd.date_range(start='2023-01-01', periods=10, freq='D')
            df = pd.DataFrame({
                'date': dates,
                'open': [100 + i for i in range(10)],
                'high': [101 + i for i in range(10)],
                'low': [99 + i for i in range(10)],
                'close': [100 + i for i in range(10)],
                'volume': [1000 + i * 10 for i in range(10)],
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

    # ── buffer_days tolerance cache-hit tests ──────────────────────────

    @patch('exchange.source.data_provider.AkshareProvider.fetch')
    def test_cache_hit_within_buffer_days(self, mock_fetch):
        """Request end_date slightly beyond cache_max but within buffer_days → cache hit (no fetch)."""
        with tempfile.TemporaryDirectory() as tmp:
            cache_file = os.path.join(tmp, '600900.csv')
            dates = pd.date_range(start='2023-01-01', periods=5, freq='D')
            df = pd.DataFrame({
                'date': dates,
                'open': [100 + i for i in range(5)],
                'high': [101 + i for i in range(5)],
                'low': [99 + i for i in range(5)],
                'close': [100 + i for i in range(5)],
                'volume': [1000 + i * 10 for i in range(5)],
            })
            df.to_csv(cache_file, index=False)

            out = get_data(
                symbol='600900', source='akshare',
                start_date='20230101', end_date='20230108',
                cache_dir=tmp, buffer_days=5,
            )
            self.assertEqual(mock_fetch.call_count, 0)
            self.assertIsNotNone(out)
            self.assertEqual(out['date'].min().strftime('%Y-%m-%d'), '2023-01-01')
            self.assertEqual(out['date'].max().strftime('%Y-%m-%d'), '2023-01-05')

    @patch('exchange.source.data_provider.AkshareProvider.fetch')
    def test_cache_miss_beyond_buffer_days(self, mock_fetch):
        """Request end_date far beyond cache_max + buffer_days → cache miss (fetch needed)."""
        with tempfile.TemporaryDirectory() as tmp:
            cache_file = os.path.join(tmp, '600900.csv')
            dates = pd.date_range(start='2023-01-01', periods=5, freq='D')
            df = pd.DataFrame({
                'date': dates,
                'open': [100 + i for i in range(5)],
                'high': [101 + i for i in range(5)],
                'low': [99 + i for i in range(5)],
                'close': [100 + i for i in range(5)],
                'volume': [1000 + i * 10 for i in range(5)],
            })
            df.to_csv(cache_file, index=False)

            mock_fetch.return_value = pd.DataFrame({
                'date': pd.to_datetime([
                    '2023-01-06', '2023-01-07', '2023-01-08',
                    '2023-01-09', '2023-01-10', '2023-01-15',
                ]),
                'open': [105, 106, 107, 108, 109, 110],
                'high': [106, 107, 108, 109, 110, 111],
                'low': [104, 105, 106, 107, 108, 109],
                'close': [105, 106, 107, 108, 109, 110],
                'volume': [1100] * 6,
            })

            out = get_data(
                symbol='600900', source='akshare',
                start_date='20230101', end_date='20230115',
                cache_dir=tmp, buffer_days=5,
            )
            self.assertEqual(mock_fetch.call_count, 1)
            self.assertIsNotNone(out)
            self.assertEqual(out['date'].min().strftime('%Y-%m-%d'), '2023-01-01')
            self.assertEqual(out['date'].max().strftime('%Y-%m-%d'), '2023-01-15')

    @patch('exchange.source.data_provider.AkshareProvider.fetch')
    def test_cache_hit_buffer_days_zero(self, mock_fetch):
        """buffer_days=0 → no tolerance; any request beyond cache_max is a miss (preserve existing behavior)."""
        with tempfile.TemporaryDirectory() as tmp:
            cache_file = os.path.join(tmp, '600900.csv')
            dates = pd.date_range(start='2023-01-01', periods=5, freq='D')
            df = pd.DataFrame({
                'date': dates,
                'open': [100 + i for i in range(5)],
                'high': [101 + i for i in range(5)],
                'low': [99 + i for i in range(5)],
                'close': [100 + i for i in range(5)],
                'volume': [1000 + i * 10 for i in range(5)],
            })
            df.to_csv(cache_file, index=False)

            mock_fetch.return_value = pd.DataFrame({
                'date': pd.to_datetime(['2023-01-06', '2023-01-07', '2023-01-08']),
                'open': [105, 106, 107],
                'high': [106, 107, 108],
                'low': [104, 105, 106],
                'close': [105, 106, 107],
                'volume': [1100] * 3,
            })

            out = get_data(
                symbol='600900', source='akshare',
                start_date='20230101', end_date='20230107',
                cache_dir=tmp, buffer_days=0,
            )
            self.assertEqual(mock_fetch.call_count, 1)
            self.assertIsNotNone(out)
            self.assertEqual(out['date'].max().strftime('%Y-%m-%d'), '2023-01-07')

    # ── small cache gap optimization tests ───────────────────────────

    @patch('exchange.source.data_provider.AkshareProvider.fetch')
    @patch('exchange.source.data_provider.BaostockProvider.fetch')
    @patch('exchange.source.data_provider.TencentProvider.fetch')
    @patch('exchange.source.data_provider.SinaProvider.fetch')
    @patch('exchange.source.data_provider.SohuProvider.fetch')
    @patch('exchange.source.data_provider.EastmoneyProvider.fetch')
    @patch('exchange.source.data_provider.CailianpressProvider.fetch')
    @patch('exchange.source.data_provider.StooqProvider.fetch')
    def test_small_cache_gap_limits_to_fast_sources(
        self,
        mock_stooq, mock_cailianpress, mock_eastmoney,
        mock_sohu, mock_sina,
        mock_tencent, mock_baostock, mock_akshare,
    ):
        """When cache has a gap ≤ 3 days, only fast sources (akshare, baostock, tencent) are tried."""
        with tempfile.TemporaryDirectory() as tmp:
            cache_file = os.path.join(tmp, '600900.csv')
            dates = pd.date_range(start='2023-01-01', periods=5, freq='D')
            cached_df = pd.DataFrame({
                'date': dates,
                'open': [10, 11, 12, 13, 14],
                'high': [11, 12, 13, 14, 15],
                'low': [9, 10, 11, 12, 13],
                'close': [10, 11, 12, 13, 14],
                'volume': [100] * 5,
            })
            cached_df.to_csv(cache_file, index=False)

            # All fast sources return no data → they are tried but fail
            mock_akshare.return_value = None
            mock_baostock.return_value = None
            mock_tencent.return_value = None
            # Remaining sources should NOT be called when gap ≤ 3
            mock_sina.side_effect = AssertionError("sina should not be called")
            mock_sohu.side_effect = AssertionError("sohu should not be called")
            mock_eastmoney.side_effect = AssertionError("eastmoney should not be called")
            mock_cailianpress.side_effect = AssertionError("cailianpress should not be called")
            mock_stooq.side_effect = AssertionError("stooq should not be called")

            # Request 2023-01-01 to 2023-01-07 (2-day gap past cache end of 2023-01-05 = beyond buffer_days tolerance)
            # Even though no provider returns data for the gap, cached partial data is returned
            out = get_data(
                symbol='600900', source='auto',
                start_date='20230101', end_date='20230107',
                cache_dir=tmp,
            )

            # Returned cached data (2023-01-01 to 2023-01-05) — partial result
            self.assertIsNotNone(out)
            self.assertEqual(len(out), 5)
            # Verify the gap was detected — fast sources were all tried
            mock_akshare.assert_called_once()
            mock_baostock.assert_called_once()
            mock_tencent.assert_called_once()
            # Slow sources were never tried (no AssertionError raised)
            mock_sina.assert_not_called()


if __name__ == '__main__':
    unittest.main()
