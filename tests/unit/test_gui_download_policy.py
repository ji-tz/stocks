import tempfile
import time
import unittest
from unittest.mock import patch

import pandas as pd

from gui import web


class TestGuiDownloadPolicy(unittest.TestCase):
    @patch('gui.web._fetch_source_df')
    def test_first_success_wins_and_late_success_discarded(self, mock_fetch):
        def _fake_fetch(_stock_code, _start, _end, source_name, _temp_root):
            if source_name == 'tencent':
                time.sleep(0.01)
                df = pd.DataFrame({
                    'date': pd.to_datetime(['2025-01-02', '2025-01-03']),
                    'open': [10.0, 10.1],
                    'high': [10.2, 10.3],
                    'low': [9.9, 10.0],
                    'close': [10.1, 10.2],
                    'volume': [1000, 1200],
                })
                return ({'source': 'tencent', 'status': 'success', 'rows': 2, 'duration_ms': 10, 'message': 'ok'}, df)

            if source_name == 'sina':
                time.sleep(0.03)
                df = pd.DataFrame({
                    'date': pd.to_datetime(['2025-01-02', '2025-01-03']),
                    'open': [20.0, 20.1],
                    'high': [20.2, 20.3],
                    'low': [19.9, 20.0],
                    'close': [20.1, 20.2],
                    'volume': [2000, 2200],
                })
                return ({'source': 'sina', 'status': 'success', 'rows': 2, 'duration_ms': 30, 'message': 'ok'}, df)

            time.sleep(0.02)
            return ({'source': source_name, 'status': 'failed', 'rows': 0, 'duration_ms': 20, 'message': 'fail'}, None)

        mock_fetch.side_effect = _fake_fetch

        with tempfile.TemporaryDirectory() as cache_dir:
            with patch('gui.web._get_cache_dir', return_value=cache_dir):
                with patch('gui.web._DOWNLOAD_SOURCES', ('akshare', 'tencent', 'sina')):
                    out_df, logs = web._download_from_all_sources('600900', '20250101', '20250110')

        self.assertIsNotNone(out_df)
        self.assertEqual(len(out_df), 2)
        # 先到达的 tencent 数据应被采用
        self.assertAlmostEqual(float(out_df.iloc[0]['open']), 10.0)

        by_source = {item['source']: item for item in logs}
        self.assertEqual(by_source['tencent']['status'], 'success')
        self.assertEqual(by_source['sina']['status'], 'discarded')
        self.assertIn('较晚到达', by_source['sina']['message'])


if __name__ == '__main__':
    unittest.main()
