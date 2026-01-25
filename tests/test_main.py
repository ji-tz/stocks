import unittest
import pandas as pd
from unittest.mock import patch
from main import get_data


class TestGetData(unittest.TestCase):
    def make_mock_df(self, n=20):
        dates = pd.date_range(end="2023-12-31", periods=n, freq="D")
        data = {
            "日期": dates.strftime("%Y-%m-%d"),
            "开盘": [100.0 + i for i in range(n)],
            "最高": [101.0 + i for i in range(n)],
            "最低": [99.0 + i for i in range(n)],
            "收盘": [100.0 + i for i in range(n)],
            "成交量": [1000 + i * 10 for i in range(n)],
        }
        return pd.DataFrame(data)

    @patch('source.data_provider.ak.stock_zh_a_hist')
    def test_get_data_shape(self, mock_hist):
        mock_hist.return_value = self.make_mock_df(20)
        df = get_data()
        # 检查字段
        self.assertListEqual(list(df.columns), ["date", "open", "high", "low", "close", "volume"])
        # 检查数据类型
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(df["date"]))
        self.assertTrue(df.shape[0] > 0)


if __name__ == "__main__":
    unittest.main()
