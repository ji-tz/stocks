"""测试数据源的复权参数配置

验证AkshareProvider和BaostockProvider使用正确的复权参数
"""
import unittest
from unittest.mock import MagicMock, patch, call
import pandas as pd


class TestAdjustmentParameters(unittest.TestCase):
    """测试复权参数配置"""

    @patch('akshare.stock_zh_a_hist')
    @patch('requests.Session')
    def test_akshare_uses_qfq_adjustment(self, mock_session_cls, mock_stock_zh_a_hist):
        """测试AkshareProvider使用前复权参数qfq"""
        from source.akshare_provider import AkshareProvider
        
        # 准备mock数据
        mock_df = pd.DataFrame({
            '日期': ['2023-01-01', '2023-01-02'],
            '开盘': [10.0, 10.5],
            '最高': [10.5, 11.0],
            '最低': [9.8, 10.2],
            '收盘': [10.2, 10.8],
            '成交量': [1000, 1500]
        })
        mock_stock_zh_a_hist.return_value = mock_df
        
        # 创建mock session
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        
        # 执行
        provider = AkshareProvider()
        result = provider.fetch(symbol='600900', start_date='20230101', end_date='20230102')
        
        # 验证调用参数
        mock_stock_zh_a_hist.assert_called_once()
        call_kwargs = mock_stock_zh_a_hist.call_args[1]
        
        # 关键：验证使用前复权参数
        self.assertEqual(call_kwargs['adjust'], 'qfq', 
                        "AkshareProvider应该使用前复权参数 adjust='qfq'")
        
        # 验证其他参数
        self.assertEqual(call_kwargs['symbol'], '600900')
        self.assertEqual(call_kwargs['period'], 'daily')
        self.assertEqual(call_kwargs['start_date'], '20230101')
        self.assertEqual(call_kwargs['end_date'], '20230102')
        
        # 验证返回数据
        self.assertIsNotNone(result)
        self.assertFalse(result.empty)
        self.assertIn('date', result.columns)
        self.assertIn('close', result.columns)

    @patch('baostock.logout')
    @patch('baostock.query_history_k_data_plus')
    @patch('baostock.login')
    def test_baostock_uses_qfq_adjustment(self, mock_login, mock_query, mock_logout):
        """测试BaostockProvider使用前复权参数adjustflag=2"""
        from source.baostock_provider import BaostockProvider
        
        # 准备mock数据
        mock_login_result = MagicMock()
        mock_login_result.error_code = "0"
        mock_login.return_value = mock_login_result
        
        mock_result = MagicMock()
        mock_result.error_code = "0"
        mock_result.fields = ['date', 'open', 'high', 'low', 'close', 'volume']
        
        # 模拟数据行
        data_rows = [
            ['2023-01-01', '10.0', '10.5', '9.8', '10.2', '1000'],
            ['2023-01-02', '10.5', '11.0', '10.2', '10.8', '1500']
        ]
        mock_result.next.side_effect = [True, True, False]
        mock_result.get_row_data.side_effect = data_rows
        
        mock_query.return_value = mock_result
        
        # 执行
        provider = BaostockProvider()
        result = provider.fetch(symbol='600900', start_date='20230101', end_date='20230102')
        
        # 验证调用参数
        mock_query.assert_called_once()
        call_args = mock_query.call_args[0]
        call_kwargs = mock_query.call_args[1]
        
        # 关键：验证使用前复权参数
        self.assertEqual(call_kwargs['adjustflag'], '2',
                        "BaostockProvider应该使用前复权参数 adjustflag='2'")
        
        # 验证其他参数
        self.assertEqual(call_args[0], 'sh.600900')
        self.assertEqual(call_kwargs['start_date'], '2023-01-01')
        self.assertEqual(call_kwargs['end_date'], '2023-01-02')
        self.assertEqual(call_kwargs['frequency'], 'd')
        
        # 验证返回数据
        self.assertIsNotNone(result)
        self.assertFalse(result.empty)
        self.assertIn('date', result.columns)
        self.assertIn('close', result.columns)
        
        # 验证调用了logout
        mock_logout.assert_called()

    def test_adjustment_consistency(self):
        """测试两个数据源使用一致的复权方式（前复权）"""
        # 这是一个文档性测试，说明两个数据源的复权方式
        
        # AkshareProvider 使用 adjust='qfq' (前复权)
        # BaostockProvider 使用 adjustflag='2' (前复权)
        
        # 前复权的特点：
        # 1. 保持最新价格不变
        # 2. 向前调整历史价格
        # 3. 便于与实盘对比
        
        self.assertTrue(True, "两个数据源都使用前复权，保持一致性")


class TestAdjustmentDocumentation(unittest.TestCase):
    """测试复权参数的文档说明"""
    
    def test_adjustment_parameter_values(self):
        """验证复权参数的可选值（文档用途）
        
        AKShare参数:
        - 不复权: ''
        - 前复权: 'qfq'
        - 后复权: 'hfq'
        
        Baostock参数:
        - 不复权: '3'
        - 前复权: '2'
        - 后复权: '1'
        
        当前配置: 统一使用前复权
        """
        
        # AKShare参数
        akshare_params = {
            '不复权': '',
            '前复权': 'qfq',
            '后复权': 'hfq'
        }
        
        # Baostock参数
        baostock_params = {
            '不复权': '3',
            '前复权': '2',
            '后复权': '1'
        }
        
        # 验证当前使用的参数
        self.assertEqual(akshare_params['前复权'], 'qfq')
        self.assertEqual(baostock_params['前复权'], '2')


if __name__ == '__main__':
    unittest.main()
