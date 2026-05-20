import unittest
from unittest.mock import patch
import pandas as pd

from source.akshare_provider import AkshareProvider


class TestAkshareProviderCompatibility(unittest.TestCase):
    @patch('akshare.fund_open_fund_info_em')
    @patch('akshare.fund_etf_hist_em')
    @patch('akshare.stock_zh_a_hist')
    @patch('requests.Session')
    def test_open_fund_param_fallback_from_fund_to_symbol(self,
                                                          _mock_session,
                                                          mock_stock,
                                                          mock_etf,
                                                          mock_open_fund):
        """当旧参数 fund 不可用时，回退到 symbol 参数并成功返回数据。"""
        mock_stock.return_value = pd.DataFrame()
        mock_etf.return_value = pd.DataFrame()
        mock_open_fund.side_effect = [
            TypeError('unexpected keyword argument: fund'),
            pd.DataFrame({
                '净值日期': ['2023-01-01', '2023-01-02'],
                '单位净值': ['1.23', '1.25'],
            }),
        ]

        provider = AkshareProvider(max_attempts=1)
        out = provider.fetch(symbol='161725', start_date='20230101', end_date='20230105')

        self.assertFalse(out.empty)
        self.assertEqual(len(out), 2)
        self.assertIn('open', out.columns)
        self.assertIn('close', out.columns)
        self.assertEqual(mock_open_fund.call_count, 2)
        first_kwargs = mock_open_fund.call_args_list[0].kwargs
        second_kwargs = mock_open_fund.call_args_list[1].kwargs
        self.assertIn('fund', first_kwargs)
        self.assertIn('symbol', second_kwargs)


if __name__ == '__main__':
    unittest.main()
