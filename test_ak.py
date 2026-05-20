import akshare as ak
import time
import pandas as pd

def test_api(name, func):
    start = time.time()
    try:
        res = func()
        duration = time.time() - start
        rows = len(res) if isinstance(res, (pd.DataFrame, list)) else 'N/A'
        print(f'接口: {name}, 耗时: {duration:.2f}s, 成功行数: {rows}')
    except Exception as e:
        duration = time.time() - start
        print(f'接口: {name}, 耗时: {duration:.2f}s, 异常: {type(e).__name__}: {str(e)}')

print('开始测试 AkShare 接口...')

test_api('ak.stock_zh_a_hist(symbol="600900")', 
         lambda: ak.stock_zh_a_hist(symbol='600900', period='daily', start_date='20250101', end_date='20250110', adjust='qfq'))

test_api('ak.fund_etf_hist_em(symbol="600900")', 
         lambda: ak.fund_etf_hist_em(symbol='600900', period='daily', start_date='20250101', end_date='20250110', adjust=''))

test_api('ak.fund_open_fund_info_em(fund="161725")', 
         lambda: ak.fund_open_fund_info_em(fund='161725', indicator='单位净值走势'))

test_api('ak.stock_zh_a_hist(symbol="161725")', 
         lambda: ak.stock_zh_a_hist(symbol='161725', period='daily', start_date='20250101', end_date='20250110', adjust='qfq'))
