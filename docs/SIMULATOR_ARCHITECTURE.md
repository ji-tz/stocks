# Simulator模块架构文档

## 概述

Simulator模块已经重新设计，采用了解耦的架构，为将来的实盘交易（real）做好准备。

## 架构设计

### 核心组件

```
simulator/
├── __init__.py              # 模块导出
├── base_engine.py           # 交易引擎抽象基类
├── simulator_engine.py      # 模拟交易引擎实现
├── real_engine.py          # 实盘交易引擎接口（预留）
└── simulator.py            # 高层Simulator类（向后兼容）
```

### 1. 抽象层 (base_engine.py)

定义了统一的交易引擎接口和数据结构：

#### 数据结构
- **Position**: 持仓信息（股数、平均成本、总成本）
- **Account**: 账户信息（现金、持仓）
- **TradeOrder**: 交易订单（日期、动作、价格、股数）
- **TradeResult**: 交易结果（成功与否、详细信息）

#### BaseEngine抽象类
```python
class BaseEngine(ABC):
    def buy(date, price) -> TradeResult
    def sell(date, price) -> TradeResult
    def get_cash() -> float
    def get_position() -> Position
    def get_account() -> Account
    def get_total_value(current_price) -> float
    def get_summary(current_price) -> Dict
```

### 2. 模拟引擎 (simulator_engine.py)

实现了基于内存的模拟交易功能：

```python
engine = SimulatorEngine(
    init_cash=100000.0,    # 初始资金
    lot_size=100,          # 交易手数
    verbose=True           # 详细日志
)

# 执行交易
result = engine.buy(date=some_date, price=100.0)
result = engine.sell(date=some_date, price=110.0)

# 查询状态
summary = engine.get_summary(current_price=105.0)
```

**特点：**
- ✅ 完整的买卖逻辑
- ✅ 自动计算平均成本
- ✅ 准确的盈亏计算
- ✅ 详细的交易日志
- ✅ 资金和持仓检查

### 3. 实盘引擎 (real_engine.py)

预留的实盘交易接口，当前未实现：

```python
class RealEngine(BaseEngine):
    def connect() -> bool
    def disconnect() -> None
    def buy(date, price) -> TradeResult
    def sell(date, price) -> TradeResult
    def get_real_time_price(symbol) -> float
    def cancel_order(order_id) -> bool
```

**将来实现时需要：**
1. 连接券商API
2. 实现真实下单
3. 处理实时行情
4. 风险控制和监控

### 4. 高层接口 (simulator.py)

提供向后兼容的Simulator类：

```python
sim = Simulator(
    lot_size=100,
    init_cash=100000.0,
    verbose=True          # 新增：详细日志开关
)

result = sim.simulate(
    df=data,
    strategy=strategy,
    symbol="600900",
    verbose=True          # 可以覆盖初始设置
)
```

## 使用示例

### 示例1：使用Simulator类（推荐）

```python
from simulator import Simulator
from solver.mean_cost_strategy import MeanCostDecision

# 创建模拟器
sim = Simulator(
    lot_size=100,
    init_cash=100000.0,
    verbose=True  # 开启详细日志
)

# 创建策略
strategy = MeanCostDecision()

# 执行模拟
result = sim.simulate(
    df=stock_data,
    strategy=strategy,
    symbol="600900"
)

# 查看结果
print(f"总交易次数: {result['trades']}")
print(f"最终资产: {result['total_value']}")
print(f"已实现盈亏: {result['realized_pl']}")
print(f"未实现盈亏: {result['unrealized_pl']}")
```

### 示例2：直接使用SimulatorEngine

```python
from simulator import SimulatorEngine
from datetime import datetime

# 创建引擎
engine = SimulatorEngine(
    init_cash=100000.0,
    lot_size=100,
    verbose=True
)

# 手动执行交易
date1 = datetime(2023, 1, 1)
result = engine.buy(date=date1, price=100.0)

date2 = datetime(2023, 1, 2)
result = engine.sell(date=date2, price=110.0)

# 获取账户摘要
summary = engine.get_summary(current_price=105.0)
print(f"现金: {summary['cash']}")
print(f"持仓: {summary['shares']}")
print(f"总资产: {summary['total_value']}")
```

### 示例3：为实盘交易预留（未来）

```python
# from simulator import RealEngine

# 创建实盘引擎
# engine = RealEngine(
#     api_key="your_api_key",
#     api_secret="your_api_secret"
# )

# 连接交易系统
# if engine.connect():
#     # 执行实盘交易
#     result = engine.buy(date=today, price=100.0)
#     result = engine.sell(date=today, price=110.0)
#     engine.disconnect()
```

## 新增功能

### 1. 详细的每日日志

开启verbose模式后，会打印每日的详细交易信息：

```
[2026-01-29] 买入成功：价格 100.00, 数量 100, 成本 10000.00, 剩余现金 40000.00
[2026-01-29] 开盘: 100.00 | 收盘: 100.00 | 操作: buy | 持仓: 100 | 成本: 100.00 | 现金: 40000.00 | 市值: 10000.00 | 总值: 50000.00 | 浮盈: 0.00
```

包括：
- 交易日期
- 开盘价/收盘价
- 执行的操作
- 持仓数量
- 平均成本
- 账户现金
- 市值
- 总资产
- 浮动盈亏

### 2. 完整的交易报告

模拟结束后打印完整报告：

```
====================================================================================================
模拟交易结束
====================================================================================================
总交易次数: 8
最终现金: 8400.00
最终持仓: 400 股
平均成本: 105.0000
最新价格: 100.0000
市值: 40000.00
总资产: 48400.00
已实现盈亏: 400.0000
未实现盈亏: -2000.0000
总盈亏: -1600.0000
收益率: -3.20%
====================================================================================================
```

### 3. 交易失败提示

当资金或持仓不足时，会有明确提示：

```
[2026-02-07] 买入失败：资金不足 (需要 10000.00, 可用 8400.00)
```

## 架构优势

1. **解耦设计**：引擎层与策略层分离，易于扩展
2. **统一接口**：SimulatorEngine和RealEngine实现相同接口，可互换
3. **向后兼容**：保留原有Simulator类，现有代码无需修改
4. **详细日志**：提供可选的详细交易日志，便于调试和分析
5. **易于测试**：清晰的接口和数据结构，便于单元测试
6. **可扩展性**：为实盘交易预留接口，未来可无缝切换

## 测试

运行所有测试：

```bash
# 运行所有simulator测试
python -m unittest tests.test_simulator -v

# 运行新的引擎测试
python -m unittest tests.test_simulator_engine -v

# 运行演示脚本
python demo_simulator.py
```

## 迁移指南

### 现有代码无需修改

现有使用Simulator的代码完全兼容，无需任何修改：

```python
# 这些代码仍然正常工作
sim = Simulator(lot_size=100, init_cash=100000.0)
result = sim.simulate(df=data, strategy=strategy)
```

### 可选：启用详细日志

如需详细日志，只需添加verbose参数：

```python
# 方式1：初始化时指定
sim = Simulator(lot_size=100, init_cash=100000.0, verbose=True)
result = sim.simulate(df=data, strategy=strategy)

# 方式2：simulate时指定
sim = Simulator(lot_size=100, init_cash=100000.0)
result = sim.simulate(df=data, strategy=strategy, verbose=True)
```

## 未来规划

1. **实盘交易支持**：完成RealEngine实现
2. **更多交易类型**：支持限价单、市价单等
3. **风险控制**：实现止损、止盈等风控机制
4. **性能优化**：优化大规模回测性能
5. **可视化增强**：提供更丰富的图表展示

## 参考文档

- [测试用例](../tests/test_simulator.py)
- [引擎测试](../tests/test_simulator_engine.py)
- [演示脚本](../demo_simulator.py)
- [主README](../README.md)
