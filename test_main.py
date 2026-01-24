import unittest
import pandas as pd
import akshare as ak
from main import get_data

class TestGetData(unittest.TestCase):
    def test_get_data_shape(self):
        df = get_data()
        # 检查字段
        self.assertListEqual(list(df.columns), ["date", "open", "high", "low", "close", "volume"])
        # 检查数据类型
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(df["date"]))
        self.assertTrue(df.shape[0] > 0)

if __name__ == "__main__":
    unittest.main()
import unittest
import pandas as pd
import akshare as ak
from main import get_data

class TestGetData(unittest.TestCase):
    def test_get_data_shape(self):
        df = get_data()
        # 检查字段
        self.assertListEqual(list(df.columns), ["date", "open", "high", "low", "close", "volume"])
        # 检查数据类型
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(df["date"]))
        self.assertTrue(df.shape[0] > 0)

if __name__ == "__main__":
    unittest.main()
