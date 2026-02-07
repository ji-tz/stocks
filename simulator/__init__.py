"""Simulator模块

提供交易模拟和实盘交易的统一接口。

模块结构：
- base_engine: 交易引擎抽象基类
- simulator_engine: 模拟交易引擎实现
- real_engine: 实盘交易引擎接口（预留）
- simulator: 通用模拟器（向后兼容的高层接口）

使用示例：

```python
# 方式1：使用Simulator类（推荐，向后兼容）
from simulator import Simulator
from solver.mean_cost_strategy import MeanCostDecision

sim = Simulator(lot_size=100, init_cash=100000, verbose=True)
strategy = MeanCostDecision()
result = sim.simulate(df=data, strategy=strategy, symbol="600900")

# 方式2：直接使用SimulatorEngine（更底层，更灵活）
from simulator import SimulatorEngine

engine = SimulatorEngine(init_cash=100000, lot_size=100, verbose=True)
# 手动控制买卖
engine.buy(date=some_date, price=10.5)
engine.sell(date=some_date, price=11.2)

# 方式3：为将来的实盘交易预留（尚未实现）
# from simulator import RealEngine
# engine = RealEngine(api_key="...", api_secret="...")
```
"""

from simulator.simulator import Simulator, simulate_mean_cost, simulate_sma
from simulator.base_engine import BaseEngine, Position, Account, TradeOrder, TradeResult
from simulator.simulator_engine import SimulatorEngine
from simulator.real_engine import RealEngine

__all__ = [
    # 高层接口
    'Simulator',
    'simulate_mean_cost',
    'simulate_sma',
    
    # 引擎接口
    'BaseEngine',
    'SimulatorEngine', 
    'RealEngine',
    
    # 数据结构
    'Position',
    'Account',
    'TradeOrder',
    'TradeResult',
]
