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

    @patch('socket.setdefaulttimeout')
    @patch('socket.getdefaulttimeout', return_value=None)
    @patch('baostock.logout')
    @patch('baostock.query_history_k_data_plus')
    @patch('baostock.login')
    def test_baostock_sets_and_restores_socket_timeout(self,
                                                       mock_login,
                                                       mock_query,
                                                       mock_logout,
                                                       _mock_get_timeout,
                                                       mock_set_timeout):
        """测试BaostockProvider会设置并恢复socket默认超时，避免网络卡死。"""
        from source.baostock_provider import BaostockProvider

        mock_login_result = MagicMock()
        mock_login_result.error_code = "0"
        mock_login.return_value = mock_login_result

        mock_result = MagicMock()
        mock_result.error_code = "0"
        mock_result.fields = ['date', 'open', 'high', 'low', 'close', 'volume']
        mock_result.next.side_effect = [True, False]
        mock_result.get_row_data.return_value = ['2023-01-01', '10.0', '10.5', '9.8', '10.2', '1000']
        mock_query.return_value = mock_result

        provider = BaostockProvider(timeout_seconds=7.5)
        out = provider.fetch(symbol='600900', start_date='20230101', end_date='20230102')

        self.assertFalse(out.empty)
        self.assertIn(call(7.5), mock_set_timeout.mock_calls)
        self.assertIn(call(None), mock_set_timeout.mock_calls)
        mock_logout.assert_called()

    def test_adjustment_consistency(self):
        """测试两个数据源使用一致的复权方式（前复权）"""
        # 验证两个数据源的复权配置一致性
        
        # 通过源代码验证配置
        from source.akshare_provider import AkshareProvider
        from source.baostock_provider import BaostockProvider
        
        # 读取源代码验证复权参数配置
        import inspect
        
        # 验证AkshareProvider的fetch方法包含adjust="qfq"
        akshare_source = inspect.getsource(AkshareProvider.fetch)
        self.assertIn('adjust="qfq"', akshare_source,
                     "AkshareProvider应使用前复权参数adjust='qfq'")
        
        # 验证BaostockProvider的fetch方法包含adjustflag="2"
        baostock_source = inspect.getsource(BaostockProvider.fetch)
        self.assertIn('adjustflag="2"', baostock_source,
                     "BaostockProvider应使用前复权参数adjustflag='2'")


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
