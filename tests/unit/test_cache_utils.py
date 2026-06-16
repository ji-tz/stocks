import os
import tempfile
import pandas as pd
import unittest

from exchange.source import data_provider as dp


class TestCacheUtils(unittest.TestCase):
    def test_merge_into_cache_creates_and_merges(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_file = os.path.join(tmp, '600900.csv')
            dates1 = pd.date_range(start='2023-01-01', periods=3, freq='D')
            df1 = pd.DataFrame(
                {
                    'date': dates1, 'open': [
                        1, 2, 3], 'high': [
                        1, 2, 3], 'low': [
                        1, 2, 3], 'close': [
                        1, 2, 3], 'volume': [
                            10, 20, 30]})
            dp._merge_into_cache(cache_file, df1)
            self.assertTrue(os.path.exists(cache_file))
            out1 = dp._read_cache(cache_file)
            self.assertEqual(len(out1), 3)

            # merge overlapping with updated value for middle date
            dates2 = pd.date_range(start='2023-01-02', periods=3, freq='D')
            df2 = pd.DataFrame({'date': dates2, 'open': [20, 21, 22], 'high': [20, 21, 22], 'low': [
                               20, 21, 22], 'close': [20, 21, 22], 'volume': [200, 210, 220]})
            dp._merge_into_cache(cache_file, df2)
            out2 = dp._read_cache(cache_file)
            # after merge should have dates 1..4
            self.assertEqual(len(out2), 4)
            # middle date (2023-01-02) should have been updated to new open value 20
            self.assertEqual(int(out2[out2['date'] == pd.Timestamp('2023-01-02')]['open'].iloc[0]), 20)


if __name__ == '__main__':
    unittest.main()
