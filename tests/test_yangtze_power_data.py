#!/usr/bin/env python3
"""
长江电力数据质量测试
验证2023-2025年期间的数据没有异常
"""
import os
import sys
import unittest
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestYangtzePowerDataQuality(unittest.TestCase):
    """测试长江电力数据质量"""
    
    def setUp(self):
        """设置测试数据"""
        cache_file = "data/600900.csv"
        if not os.path.exists(cache_file):
            self.skipTest("缓存文件不存在")
        
        self.df = pd.read_csv(cache_file, parse_dates=['date'])
        
    def test_no_extreme_price_changes_after_2020(self):
        """测试2020年后没有异常的价格波动（单日涨跌幅不超过30%）"""
        if len(self.df) <= 1:
            self.skipTest("数据不足")
        
        # 只检查2020年之后的数据，排除早期可能的除权除息等历史事件
        df_recent = self.df[self.df['date'] >= '2020-01-01'].copy()
        if len(df_recent) <= 1:
            self.skipTest("2020年后数据不足")
        
        df_recent['price_change'] = df_recent['close'].pct_change()
        
        # 检查是否有单日涨跌幅超过30%的情况
        extreme_changes = df_recent[df_recent['price_change'].abs() > 0.30]
        
        self.assertEqual(
            len(extreme_changes), 
            0, 
            f"2020年后发现{len(extreme_changes)}个异常的价格波动（涨跌幅>30%）"
        )
    
    def test_no_low_volume_with_high_price(self):
        """测试没有成交量异常小的高价股情况"""
        # 价格大于50元但成交量小于1万股的情况
        anomalies = self.df[(self.df['close'] > 50) & (self.df['volume'] < 10000)]
        
        self.assertEqual(
            len(anomalies),
            0,
            f"发现{len(anomalies)}个高价但成交量异常小的记录"
        )
    
    def test_no_linear_increment_pattern(self):
        """测试没有明显的线性递增模式（测试数据特征）"""
        # 检查连续10天以上的价格线性递增
        if len(self.df) < 10:
            self.skipTest("数据不足")
        
        has_pattern = False
        for i in range(len(self.df) - 10):
            window = self.df.iloc[i:i+10]
            close_prices = window['close'].values
            
            # 检查是否为等差数列
            diffs = close_prices[1:] - close_prices[:-1]
            if len(set(diffs.round(2))) == 1 and diffs[0] > 0.5:
                has_pattern = True
                break
        
        self.assertFalse(
            has_pattern,
            "发现价格呈线性递增模式（测试数据特征）"
        )
    
    def test_2023_data_range(self):
        """测试2023年数据价格范围合理"""
        df_2023 = self.df[self.df['date'].dt.year == 2023]
        
        if len(df_2023) == 0:
            self.skipTest("没有2023年的数据")
        
        min_price = df_2023['close'].min()
        max_price = df_2023['close'].max()
        
        # 长江电力2023年的合理价格范围应该在15-35元之间
        self.assertGreater(min_price, 15, f"2023年最低价{min_price}过低")
        self.assertLess(max_price, 35, f"2023年最高价{max_price}过高，可能是异常数据")
        
    def test_2023_nov_to_2024_jan_continuity(self):
        """测试2023年11月到2024年1月的数据连续性"""
        period = self.df[
            (self.df['date'] >= '2023-11-01') & 
            (self.df['date'] <= '2024-01-05')
        ]
        
        if len(period) < 2:
            self.skipTest("该时间段数据不足")
        
        # 检查价格变化是否合理（不应该有从22元突然跳到100元的情况）
        period_sorted = period.sort_values('date')
        max_jump = 0
        for i in range(1, len(period_sorted)):
            prev_close = period_sorted.iloc[i-1]['close']
            curr_close = period_sorted.iloc[i]['close']
            jump = abs(curr_close - prev_close) / prev_close
            max_jump = max(max_jump, jump)
        
        self.assertLess(
            max_jump, 
            0.30, 
            f"2023年11月到2024年1月期间有异常的价格跳变（{max_jump:.2%}）"
        )
    
    def test_all_prices_positive(self):
        """测试所有价格都是正数"""
        for col in ['open', 'high', 'low', 'close']:
            min_val = self.df[col].min()
            self.assertGreater(
                min_val, 
                0, 
                f"{col}列存在零值或负值: {min_val}"
            )
    
    def test_price_logic(self):
        """测试价格逻辑（最低价不应该高于最高价）"""
        invalid = self.df[self.df['low'] > self.df['high']]
        
        self.assertEqual(
            len(invalid),
            0,
            f"发现{len(invalid)}条最低价>最高价的记录"
        )


if __name__ == '__main__':
    unittest.main()
