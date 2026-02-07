#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
定投策略演示脚本

演示如何使用定投策略进行回测，并展示详细的交易日志。
"""
import sys
from simulator.simulator import simulate_fixed_amount


def main():
    """运行定投策略演示"""
    print("=" * 100)
    print("定投策略（Fixed Amount Investment Strategy）演示")
    print("=" * 100)
    print()
    print("策略说明：")
    print("  - 每天投入固定金额（默认 1000 元）")
    print("  - 根据当前价格自动计算购买股数")
    print("  - 只买不卖，持续定投")
    print("  - 适合长期投资，平滑市场波动")
    print()
    print("=" * 100)
    print()
    
    # 运行回测
    try:
        result = simulate_fixed_amount(
            symbol="600900",           # 长江电力
            start_date="20240101",     # 2024年1月1日开始
            end_date="20241231",       # 2024年12月31日结束
            fixed_amount=1000.0,       # 每次投入 1000 元
            lot_size=100,              # 100股为1手
            init_cash=100000.0,        # 初始资金 10万
            verbose=True               # 显示详细日志
        )
        
        # 打印汇总结果
        print("\n" + "=" * 100)
        print("回测结果汇总")
        print("=" * 100)
        print(f"股票代码: {result['symbol']}")
        print(f"回测区间: {result['start_date']} 至 {result['end_date']}")
        print(f"初始资金: {result['init_cash']:.2f} 元")
        print(f"最终现金: {result['cash']:.2f} 元")
        print(f"最终持仓: {result['shares']} 股")
        print(f"最新价格: {result['last_price']:.4f} 元")
        print(f"市值: {result['market_value']:.2f} 元")
        print(f"总资产: {result['total_value']:.2f} 元")
        print(f"总交易次数: {result['trades']}")
        print(f"已实现盈亏: {result['realized_pl']:.4f} 元")
        print(f"未实现盈亏: {result['unrealized_pl']:.4f} 元")
        
        # 计算总收益率
        total_pl = result['realized_pl'] + result['unrealized_pl']
        return_rate = (total_pl / result['init_cash']) * 100
        print(f"总盈亏: {total_pl:.4f} 元")
        print(f"收益率: {return_rate:.2f}%")
        
        # 计算实际投入金额
        invested = result['init_cash'] - result['cash']
        print(f"实际投入: {invested:.2f} 元")
        
        # 计算平均成本
        if result['shares'] > 0:
            avg_cost = invested / result['shares']
            print(f"平均成本: {avg_cost:.4f} 元/股")
        
        print("=" * 100)
        print()
        print("✅ 定投策略演示完成！")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ 错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
