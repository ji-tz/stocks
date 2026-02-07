#!/usr/bin/env python3
"""
演示增强的simulator模块功能

展示：
1. 详细的每日交易日志
2. 新的解耦架构
3. SimulatorEngine直接使用
"""
import pandas as pd
from datetime import datetime, timedelta
from simulator import Simulator, SimulatorEngine
from solver.mean_cost_strategy import MeanCostDecision


def create_demo_data(days=10, start_price=100.0):
    """创建演示数据：价格先涨后跌"""
    dates = pd.date_range(end=datetime.now(), periods=days, freq="D")
    prices = []
    for i in range(days):
        if i < days // 2:
            # 前半段上涨
            prices.append(start_price + i * 2)
        else:
            # 后半段下跌
            prices.append(start_price + (days - i - 1) * 2)
    
    df = pd.DataFrame({
        "date": dates,
        "open": prices,
        "high": [p + 1 for p in prices],
        "low": [p - 1 for p in prices],
        "close": prices,
        "volume": [10000 + i * 100 for i in range(days)],
    })
    return df


def demo_simulator_verbose():
    """演示1：使用Simulator类的verbose模式"""
    print("=" * 100)
    print("演示1：使用Simulator类 + verbose模式")
    print("=" * 100)
    
    df = create_demo_data(days=10, start_price=100.0)
    sim = Simulator(lot_size=100, init_cash=50000.0, verbose=True)
    strategy = MeanCostDecision()
    
    result = sim.simulate(df=df, strategy=strategy, symbol="DEMO001")
    
    print("\n最终结果摘要：")
    print(f"  交易次数: {result['trades']}")
    print(f"  最终总资产: {result['total_value']:.2f}")
    print(f"  已实现盈亏: {result['realized_pl']:.4f}")
    print(f"  未实现盈亏: {result['unrealized_pl']:.4f}")
    print()


def demo_engine_direct():
    """演示2：直接使用SimulatorEngine"""
    print("=" * 100)
    print("演示2：直接使用SimulatorEngine（底层API）")
    print("=" * 100)
    
    engine = SimulatorEngine(init_cash=100000.0, lot_size=100, verbose=True)
    
    print("\n执行手动交易序列：")
    
    # 模拟几天的交易
    date1 = datetime(2023, 1, 1)
    print("\n第1天：开盘价100，买入")
    result1 = engine.buy(date=date1, price=100.0)
    summary1 = engine.get_summary(current_price=102.0)
    print(f"  收盘价102，账户总值: {summary1['total_value']:.2f}, 浮盈: {summary1['unrealized_pl']:.2f}")
    
    date2 = datetime(2023, 1, 2)
    print("\n第2天：开盘价105，再次买入")
    result2 = engine.buy(date=date2, price=105.0)
    summary2 = engine.get_summary(current_price=107.0)
    print(f"  收盘价107，账户总值: {summary2['total_value']:.2f}, 浮盈: {summary2['unrealized_pl']:.2f}")
    
    date3 = datetime(2023, 1, 3)
    print("\n第3天：开盘价110，卖出一次")
    result3 = engine.sell(date=date3, price=110.0)
    summary3 = engine.get_summary(current_price=108.0)
    print(f"  收盘价108，账户总值: {summary3['total_value']:.2f}")
    print(f"  已实现盈亏: {summary3['realized_pl']:.2f}, 浮盈: {summary3['unrealized_pl']:.2f}")
    
    print(f"\n总交易次数: {engine.trade_count}")
    print()


def demo_architecture():
    """演示3：展示新架构的解耦性"""
    print("=" * 100)
    print("演示3：展示架构解耦 - 可以轻松切换引擎")
    print("=" * 100)
    
    print("\n当前可用的交易引擎：")
    print("  1. SimulatorEngine - 模拟交易引擎（已实现，用于回测）")
    print("  2. RealEngine - 实盘交易引擎（接口已预留，待实现）")
    
    print("\n架构特点：")
    print("  ✓ BaseEngine 定义统一接口")
    print("  ✓ SimulatorEngine 实现模拟交易")
    print("  ✓ RealEngine 预留实盘交易接口")
    print("  ✓ Simulator 类作为高层封装，向后兼容")
    print("  ✓ 所有引擎共享相同的数据结构：Position, Account, TradeOrder, TradeResult")
    
    print("\n切换引擎示例（伪代码）：")
    print("  # 回测模式")
    print("  engine = SimulatorEngine(init_cash=100000)")
    print("  ")
    print("  # 实盘模式（将来）")
    print("  # engine = RealEngine(api_key='...', api_secret='...')")
    print("  # engine.connect()")
    print("  ")
    print("  # 统一的交易接口")
    print("  engine.buy(date=today, price=100.0)")
    print("  engine.sell(date=today, price=110.0)")
    print()


if __name__ == "__main__":
    print("\n")
    print("╔═══════════════════════════════════════════════════════════════════════════════════╗")
    print("║                    Simulator 模块增强功能演示                                      ║")
    print("╚═══════════════════════════════════════════════════════════════════════════════════╝")
    print("\n")
    
    # 演示1：Simulator + verbose
    demo_simulator_verbose()
    input("按Enter继续下一个演示...")
    
    # 演示2：直接使用Engine
    demo_engine_direct()
    input("按Enter继续下一个演示...")
    
    # 演示3：架构说明
    demo_architecture()
    
    print("\n演示结束！\n")
