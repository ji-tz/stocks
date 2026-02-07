#!/usr/bin/env python3
"""
股票定投集成测试（支持随机股票选择）
测试定投策略在实际股票上的表现
默认随机从股票池中选择，也可指定特定股票代码
"""
import os
import sys
import json
from typing import Dict, Any

# 确保项目根目录在 sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from simulator.simulator import simulate_mean_cost
from tests.test_utils import get_random_stock_code
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
import pandas as pd


def run_yangtze_power_test(
    symbol: str = None,
    start_date: str = "20200101",
    end_date: str = "20221231",
    lot_size: int = 100,
    init_cash: float = 1000000.0,
    source: str = "auto"
) -> Dict[str, Any]:
    """
    运行股票定投测试（支持随机选择）
    
    Args:
        symbol: 股票代码，如果为None则随机选择
        start_date: 开始日期
        end_date: 结束日期
        lot_size: 每手股数
        init_cash: 初始资金
        source: 数据源
    
    Returns:
        测试结果字典
    """
    # 如果未指定股票代码，随机选择
    if symbol is None:
        symbol = get_random_stock_code()
        print("=" * 60)
        print(f"随机选择股票: {symbol}")
    else:
        print("=" * 60)
        print(f"指定股票: {symbol}")
    
    print("股票定投集成测试 (2020-2022)")
    print("=" * 60)
    print(f"股票代码: {symbol}")
    print(f"测试期间: {start_date} - {end_date}")
    print(f"初始资金: ¥{init_cash:,.2f}")
    print(f"每手股数: {lot_size}")
    print("-" * 60)
    
    # 运行定投模拟
    result = simulate_mean_cost(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        lot_size=lot_size,
        init_cash=init_cash,
        source=source
    )
    
    # 打印结果
    print("\n" + "=" * 60)
    print("测试结果")
    print("=" * 60)
    print(f"股票名称: {result.get('symbol', symbol)}")
    print(f"开始日期: {result.get('start_date', start_date)}")
    print(f"结束日期: {result.get('end_date', end_date)}")
    print(f"初始资金: ¥{result.get('init_cash', init_cash):,.2f}")
    print(f"最终资金: ¥{result.get('cash', 0):,.2f}")
    print(f"持有市值: ¥{result.get('market_value', 0):,.2f}")
    print(f"总资产: ¥{result.get('total_value', 0):,.2f}")
    print(f"已实现盈亏: ¥{result.get('realized_pl', 0):,.2f}")
    print(f"未实现盈亏: ¥{result.get('unrealized_pl', 0):,.2f}")
    profit = result.get('total_value', init_cash) - init_cash
    return_rate = profit / init_cash if init_cash > 0 else 0
    print(f"总收益: ¥{profit:,.2f}")
    print(f"收益率: {return_rate:.2%}")
    print(f"交易次数: {result.get('trades', 0)}")
    print(f"持有股数: {result.get('shares', 0)}")
    print(f"平均成本: ¥{result.get('avg_cost', 0):.2f}")
    print("=" * 60)
    
    return result


def save_result_chart(result: Dict[str, Any], output_path: str = "screenshots/yangtze_power_test.png"):
    """
    保存测试结果图表
    
    Args:
        result: 测试结果
        output_path: 输出文件路径
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 创建图表
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # 设置中文字体 - 使用fallback机制确保在不同系统上都能正常显示
    import matplotlib.font_manager as fm
    
    # 尝试使用中文字体，如果不可用则使用系统默认字体
    # 按优先级列出常见中文字体：Windows、macOS、Linux
    chinese_fonts = [
        'SimHei',                    # Windows 黑体
        'Microsoft YaHei',           # Windows 微软雅黑
        'STHeiti',                   # macOS 黑体
        'Arial Unicode MS',          # macOS
        'WenQuanYi Zen Hei',        # Linux 文泉驿正黑
        'WenQuanYi Micro Hei',      # Linux 文泉驿微米黑
        'Noto Sans CJK SC',         # Linux Noto 思源黑体
        'Droid Sans Fallback',      # Android/Linux
    ]
    
    available_font = None
    all_font_names = [f.name for f in fm.fontManager.ttflist]
    
    for font in chinese_fonts:
        if font in all_font_names:
            available_font = font
            print(f"使用中文字体: {available_font}")
            break
    
    if available_font:
        plt.rcParams['font.sans-serif'] = [available_font]
        plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
    else:
        # 如果没有中文字体，使用默认字体但可能无法正确显示中文
        print("警告: 未找到中文字体，图表中的中文可能无法正确显示")
        print(f"可用字体示例: {all_font_names[:5]}")
    
    # 图1: 资产价值变化
    history = result.get('history', [])
    if history:
        df_history = pd.DataFrame(history)
        dates = pd.to_datetime(df_history['date'])
        total_values = df_history['total_value']
        
        ax1.plot(dates, total_values, 'b-', linewidth=2, label='总资产')
        ax1.axhline(y=result.get('init_cash', 0), color='r', linestyle='--', label='初始资金')
        ax1.set_xlabel('日期', fontsize=12)
        ax1.set_ylabel('资产价值 (¥)', fontsize=12)
        symbol_display = result.get('symbol', 'Unknown')
        ax1.set_title(f'{symbol_display} 定投资产变化 (2020-2022)', fontsize=14, fontweight='bold')
        ax1.legend(fontsize=10)
        ax1.grid(True, alpha=0.3)
        ax1.ticklabel_format(style='plain', axis='y')
    
    # 图2: 收益统计
    init_cash_val = result.get('init_cash', 0)
    total_value_val = result.get('total_value', 0)
    profit = total_value_val - init_cash_val
    
    stats = {
        '初始资金': init_cash_val,
        '最终总资产': total_value_val,
        '总收益': profit
    }
    
    colors = ['#3498db', '#2ecc71', '#e74c3c' if profit < 0 else '#2ecc71']
    bars = ax2.bar(stats.keys(), stats.values(), color=colors, alpha=0.7)
    
    # 在柱状图上显示数值
    for bar in bars:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'¥{height:,.0f}',
                ha='center', va='bottom', fontsize=10)
    
    ax2.set_ylabel('金额 (¥)', fontsize=12)
    ax2.set_title('收益统计', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='y')
    ax2.ticklabel_format(style='plain', axis='y')
    
    # 添加收益率文本
    return_rate = profit / init_cash_val if init_cash_val > 0 else 0
    color = 'red' if return_rate < 0 else 'green'
    ax2.text(0.5, 0.95, f'收益率: {return_rate:.2%}',
            transform=ax2.transAxes,
            fontsize=14, fontweight='bold',
            color=color,
            ha='center', va='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n图表已保存到: {output_path}")
    plt.close()


def save_result_json(result: Dict[str, Any], output_path: str = "test_results/yangtze_power_test.json"):
    """保存测试结果为JSON"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    print(f"结果JSON已保存到: {output_path}")


if __name__ == "__main__":
    try:
        # 运行测试
        result = run_yangtze_power_test()
        
        # 保存结果
        save_result_chart(result)
        save_result_json(result)
        
        print("\n✓ 股票定投集成测试完成!")
        
        # 返回成功退出码
        sys.exit(0)
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
