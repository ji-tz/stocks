#!/usr/bin/env python3
"""
数据缓存清理工具
用于检测和清理缓存文件中的异常数据
"""
import os
import sys
import pandas as pd
from typing import List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def detect_anomalies(df: pd.DataFrame, symbol: str) -> List[Tuple[int, str]]:
    """
    检测数据异常
    
    Args:
        df: 股票数据DataFrame
        symbol: 股票代码
    
    Returns:
        异常列表 [(行号, 原因)]
    """
    anomalies = []
    
    # 检查1: 单日涨跌幅超过30%（排除首日）
    if len(df) > 1:
        df_temp = df.copy()
        df_temp['price_change'] = df_temp['close'].pct_change()
        extreme_changes = df_temp[df_temp['price_change'].abs() > 0.30]
        for idx in extreme_changes.index:
            anomalies.append((idx, f"单日涨跌幅{extreme_changes.loc[idx, 'price_change']:.2%}超过30%"))
    
    # 检查2: 成交量异常小（小于1万股，但价格正常）
    low_volume = df[df['volume'] < 10000]
    for idx in low_volume.index:
        if df.loc[idx, 'close'] > 50:  # 价格大于50元但成交量小于1万
            anomalies.append((idx, f"成交量异常小: {df.loc[idx, 'volume']}股"))
    
    # 检查3: 价格呈现明显的线性递增模式（测试数据特征）
    if len(df) > 10:
        # 检查连续10天以上的价格线性递增
        for i in range(len(df) - 10):
            window = df.iloc[i:i+10]
            close_prices = window['close'].values
            # 检查是否为等差数列（差值的方差接近0）
            diffs = close_prices[1:] - close_prices[:-1]
            if len(set(diffs.round(2))) == 1 and diffs[0] > 0.5:  # 完全等差且每天增长>0.5元
                for idx in window.index:
                    anomalies.append((idx, f"价格呈线性递增模式（测试数据特征）"))
                break
    
    return anomalies


def clean_cache_file(cache_file: str, symbol: str, dry_run: bool = True) -> bool:
    """
    清理缓存文件中的异常数据
    
    Args:
        cache_file: 缓存文件路径
        symbol: 股票代码
        dry_run: 是否只是检查不实际修改
    
    Returns:
        是否发现异常
    """
    if not os.path.exists(cache_file):
        print(f"✓ 缓存文件不存在: {cache_file}")
        return False
    
    try:
        df = pd.read_csv(cache_file, parse_dates=['date'])
        print(f"\n{'='*80}")
        print(f"检查缓存文件: {cache_file}")
        print(f"股票代码: {symbol}")
        print(f"数据记录数: {len(df)}")
        print(f"{'='*80}")
        
        # 检测异常
        anomalies = detect_anomalies(df, symbol)
        
        if not anomalies:
            print("\n✓ 未发现异常数据")
            return False
        
        # 去重异常行号
        anomaly_indices = sorted(set([idx for idx, _ in anomalies]))
        print(f"\n⚠ 发现 {len(anomaly_indices)} 行异常数据:")
        
        # 显示异常详情
        anomaly_reasons = {}
        for idx, reason in anomalies:
            if idx not in anomaly_reasons:
                anomaly_reasons[idx] = []
            if reason not in anomaly_reasons[idx]:
                anomaly_reasons[idx].append(reason)
        
        for idx in anomaly_indices[:20]:  # 最多显示20行
            date = df.loc[idx, 'date']
            close = df.loc[idx, 'close']
            volume = df.loc[idx, 'volume']
            reasons = "; ".join(anomaly_reasons[idx])
            print(f"  行{idx}: {date.strftime('%Y-%m-%d')} 收盘价:{close:.2f} 成交量:{volume:.0f} - {reasons}")
        
        if len(anomaly_indices) > 20:
            print(f"  ... 还有 {len(anomaly_indices) - 20} 行异常数据")
        
        if dry_run:
            print(f"\n[预览模式] 将删除 {len(anomaly_indices)} 行异常数据")
            print(f"剩余数据: {len(df) - len(anomaly_indices)} 行")
            return True
        
        # 删除异常数据
        df_cleaned = df.drop(anomaly_indices).reset_index(drop=True)
        
        # 保存清理后的数据
        backup_file = cache_file + ".backup"
        os.rename(cache_file, backup_file)
        print(f"\n✓ 原文件已备份到: {backup_file}")
        
        df_cleaned.to_csv(cache_file, index=False)
        print(f"✓ 已保存清理后的数据: {len(df_cleaned)} 行")
        print(f"✓ 删除了 {len(anomaly_indices)} 行异常数据")
        
        return True
        
    except Exception as e:
        print(f"\n✗ 处理失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def clean_all_cache(cache_dir: str = "data", dry_run: bool = True):
    """
    清理所有缓存文件
    
    Args:
        cache_dir: 缓存目录
        dry_run: 是否只是检查不实际修改
    """
    if not os.path.exists(cache_dir):
        print(f"缓存目录不存在: {cache_dir}")
        return
    
    csv_files = [f for f in os.listdir(cache_dir) if f.endswith('.csv') and not f.endswith('.backup')]
    
    if not csv_files:
        print(f"缓存目录中没有CSV文件: {cache_dir}")
        return
    
    print(f"{'='*80}")
    print(f"数据缓存清理工具")
    print(f"缓存目录: {cache_dir}")
    print(f"CSV文件数: {len(csv_files)}")
    print(f"模式: {'预览模式（不会修改文件）' if dry_run else '清理模式（会修改文件）'}")
    print(f"{'='*80}")
    
    cleaned_count = 0
    for csv_file in sorted(csv_files):
        symbol = os.path.splitext(csv_file)[0]
        cache_file = os.path.join(cache_dir, csv_file)
        
        if clean_cache_file(cache_file, symbol, dry_run):
            cleaned_count += 1
    
    print(f"\n{'='*80}")
    print(f"清理完成！")
    print(f"检查了 {len(csv_files)} 个文件")
    print(f"发现异常: {cleaned_count} 个文件")
    if dry_run:
        print(f"\n提示: 这是预览模式，没有实际修改文件")
        print(f"要真正清理数据，请运行: python tools/clean_data_cache.py --apply")
    print(f"{'='*80}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="数据缓存清理工具")
    parser.add_argument("--cache-dir", default="data", help="缓存目录路径")
    parser.add_argument("--symbol", help="只清理指定股票代码")
    parser.add_argument("--apply", action="store_true", help="实际执行清理（默认只预览）")
    
    args = parser.parse_args()
    
    dry_run = not args.apply
    
    if args.symbol:
        # 清理指定股票
        cache_file = os.path.join(args.cache_dir, f"{args.symbol}.csv")
        clean_cache_file(cache_file, args.symbol, dry_run)
    else:
        # 清理所有缓存
        clean_all_cache(args.cache_dir, dry_run)
