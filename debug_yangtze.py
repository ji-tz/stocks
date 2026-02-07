#!/usr/bin/env python3
"""
调试长江电力股价数据
检查2023-2025年之间的数据异常
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from source.data_provider import get_data
    import pandas as pd
    
    print("=" * 80)
    print("长江电力（600900）股价数据检查")
    print("=" * 80)
    
    # 获取长江电力数据
    symbol = "600900"
    start_date = "20230101"
    end_date = "20251231"
    
    print(f"\n正在获取 {symbol} 从 {start_date} 到 {end_date} 的数据...")
    
    try:
        df = get_data(symbol=symbol, source="auto", start_date=start_date, end_date=end_date)
        
        print(f"\n✓ 成功获取数据，共 {len(df)} 条记录")
        print(f"\n数据概览:")
        print(df.head(10))
        print("\n...")
        print(df.tail(10))
        
        # 检查数据统计
        print(f"\n数据统计:")
        print(df[['open', 'high', 'low', 'close', 'volume']].describe())
        
        # 检查是否有异常波动
        print(f"\n检查异常波动:")
        df['price_change'] = df['close'].pct_change()
        df['price_change_abs'] = df['price_change'].abs()
        
        # 找出单日涨跌幅超过10%的情况
        abnormal = df[df['price_change_abs'] > 0.10].copy()
        if len(abnormal) > 0:
            print(f"\n⚠ 发现 {len(abnormal)} 天的涨跌幅超过10%:")
            print(abnormal[['date', 'open', 'high', 'low', 'close', 'volume', 'price_change']])
        else:
            print("\n✓ 未发现单日涨跌幅超过10%的异常情况")
        
        # 检查是否有缺失值
        print(f"\n检查缺失值:")
        missing = df[['open', 'high', 'low', 'close', 'volume']].isna().sum()
        print(missing)
        if missing.sum() > 0:
            print("\n⚠ 存在缺失值的行:")
            print(df[df.isna().any(axis=1)])
        
        # 检查是否有零值或负值
        print(f"\n检查零值或负值:")
        for col in ['open', 'high', 'low', 'close']:
            zero_or_neg = df[df[col] <= 0]
            if len(zero_or_neg) > 0:
                print(f"\n⚠ {col} 列存在 {len(zero_or_neg)} 个零值或负值:")
                print(zero_or_neg[['date', col]])
        
        # 检查是否有价格不合理的情况（例如，最低价>最高价）
        print(f"\n检查价格逻辑:")
        invalid_price = df[df['low'] > df['high']]
        if len(invalid_price) > 0:
            print(f"\n⚠ 发现 {len(invalid_price)} 天的最低价>最高价:")
            print(invalid_price[['date', 'open', 'high', 'low', 'close']])
        else:
            print("✓ 价格逻辑正常（最低价≤最高价）")
        
        # 按年份分组统计
        print(f"\n按年份统计:")
        df['year'] = df['date'].dt.year
        yearly_stats = df.groupby('year')['close'].agg(['count', 'min', 'max', 'mean'])
        print(yearly_stats)
        
        # 绘制价格走势图
        print(f"\n正在生成价格走势图...")
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        
        plt.figure(figsize=(15, 8))
        plt.plot(df['date'], df['close'], linewidth=1.5, label='收盘价')
        plt.xlabel('日期')
        plt.ylabel('价格 (元)')
        plt.title(f'{symbol} 长江电力 股价走势 (2023-2025)')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        os.makedirs('debug_output', exist_ok=True)
        output_file = 'debug_output/yangtze_power_price_chart.png'
        plt.savefig(output_file, dpi=150)
        print(f"✓ 价格走势图已保存到: {output_file}")
        plt.close()
        
    except Exception as e:
        print(f"\n✗ 获取数据失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
except Exception as e:
    print(f"\n✗ 导入模块失败: {e}")
    import traceback
    traceback.print_exc()
    print("\n提示: 请先安装依赖: pip install -r requirements.txt")
    sys.exit(1)

print("\n" + "=" * 80)
print("检查完成!")
print("=" * 80)
