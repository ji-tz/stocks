import os
import tempfile
import pandas as pd
import unittest

from source.data_provider import get_data


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


if __name__ == '__main__':
    unittest.main()
