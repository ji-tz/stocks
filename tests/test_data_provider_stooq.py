import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from source.data_provider import get_data


class TestDataProviderStooqFallback(unittest.TestCase):
    @patch('source.data_provider._fetch_from_cailianpress')
    @patch('source.data_provider._fetch_from_eastmoney')
    @patch('source.data_provider._fetch_from_sohu')
    @patch('source.data_provider._fetch_from_sina')
    @patch('source.data_provider._fetch_from_tencent')
    @patch('source.data_provider._fetch_from_stooq')
    @patch('source.data_provider.BaostockProvider.fetch')
    @patch('source.data_provider.AkshareProvider.fetch')
    def test_auto_fallback_to_stooq_when_primary_sources_fail(self,
                                                              mock_ak,
                                                              mock_bs,
                                                              mock_stooq,
                                                              mock_tencent,
                                                              mock_sina,
                                                              mock_sohu,
                                                              mock_eastmoney,
                                                              mock_cls):
        mock_ak.side_effect = RuntimeError('akshare down')
        mock_bs.side_effect = RuntimeError('baostock down')
        mock_tencent.side_effect = RuntimeError('tencent down')
        mock_sina.side_effect = RuntimeError('sina down')
        mock_sohu.side_effect = RuntimeError('sohu down')
        mock_eastmoney.side_effect = RuntimeError('eastmoney down')
        mock_cls.side_effect = RuntimeError('cailianpress down')
        mock_stooq.return_value = pd.DataFrame({
            'date': pd.to_datetime(['2025-01-02', '2025-01-03']),
            'open': [28.36, 28.06],
            'high': [28.58, 28.28],
            'low': [27.93, 27.70],
            'close': [28.05, 27.85],
            'volume': [1041220, 946323],
        })

        with tempfile.TemporaryDirectory() as tmp:
            out = get_data(
                symbol='600900',
                source='auto',
                start_date='20250101',
                end_date='20250110',
                cache_dir=tmp,
                force_refresh=True,
            )

        self.assertEqual(len(out), 2)
        self.assertEqual(mock_ak.call_count, 1)
        self.assertEqual(mock_bs.call_count, 1)
        self.assertEqual(mock_tencent.call_count, 1)
        self.assertEqual(mock_sina.call_count, 1)
        self.assertEqual(mock_sohu.call_count, 1)
        self.assertEqual(mock_eastmoney.call_count, 1)
        self.assertEqual(mock_cls.call_count, 1)
        self.assertEqual(mock_stooq.call_count, 1)

    @patch('source.data_provider._fetch_from_cailianpress')
    @patch('source.data_provider._fetch_from_eastmoney')
    @patch('source.data_provider._fetch_from_sohu')
    @patch('source.data_provider._fetch_from_sina')
    @patch('source.data_provider._fetch_from_tencent')
    @patch('source.data_provider.BaostockProvider.fetch')
    @patch('source.data_provider.AkshareProvider.fetch')
    def test_auto_fallback_to_tencent_when_primary_sources_fail(self,
                                                                mock_ak,
                                                                mock_bs,
                                                                mock_tencent,
                                                                mock_sina,
                                                                mock_sohu,
                                                                mock_eastmoney,
                                                                mock_cls):
        mock_ak.side_effect = RuntimeError('akshare down')
        mock_bs.side_effect = RuntimeError('baostock down')
        mock_tencent.return_value = pd.DataFrame({
            'date': pd.to_datetime(['2025-01-02', '2025-01-03']),
            'open': [28.36, 28.06],
            'high': [28.58, 28.28],
            'low': [27.93, 27.70],
            'close': [28.05, 27.85],
            'volume': [1041220, 946323],
        })

        with tempfile.TemporaryDirectory() as tmp:
            out = get_data(
                symbol='600900',
                source='auto',
                start_date='20250101',
                end_date='20250110',
                cache_dir=tmp,
                force_refresh=True,
            )

        self.assertEqual(len(out), 2)
        self.assertEqual(mock_ak.call_count, 1)
        self.assertEqual(mock_bs.call_count, 1)
        self.assertEqual(mock_tencent.call_count, 1)
        self.assertEqual(mock_sina.call_count, 0)
        self.assertEqual(mock_sohu.call_count, 0)
        self.assertEqual(mock_eastmoney.call_count, 0)
        self.assertEqual(mock_cls.call_count, 0)


if __name__ == '__main__':
    unittest.main()
