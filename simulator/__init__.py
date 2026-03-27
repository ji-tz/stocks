"""Simulator 模块

提供股票交易所统一接口。

模块结构：
- exchange_interface: 股票交易所统一接口（StockExchange）
- backtest/: 回测仿真实现
- realtime/: 实时仿真实现
- live/: 实盘交易实现（预留）
- simulator: 通用策略回测执行器（向后兼容）

使用示例：

```python
# 方式1：使用Simulator类（推荐，向后兼容）
from simulator import Simulator
from solver.mean_cost_strategy import MeanCostDecision

sim = Simulator(lot_size=100, init_cash=100000, verbose=True)
strategy = MeanCostDecision()
result = sim.simulate(df=data, strategy=strategy, symbol="600900")

# 方式2：直接使用交易所实现（接口一致）
from simulator import BacktestExchange

engine = BacktestExchange(init_cash=100000, lot_size=100, verbose=True)
# 手动控制买卖
engine.buy(date=some_date, price=10.5)
engine.sell(date=some_date, price=11.2)

# 方式3：为将来的实盘交易预留（尚未实现）
# from simulator import LiveExchange
# engine = LiveExchange(api_key="...", api_secret="...")
```
"""

from simulator.simulator import BacktestExchangeRunner, Simulator, simulate_fixed_amount, simulate_mean_cost, simulate_sma
from simulator.exchange_interface import StockExchange
from simulator.backtest.exchange import BacktestExchange
from simulator.realtime.exchange import RealtimeSimExchange
from simulator.live.exchange import LiveExchange
from simulator.base_engine import BaseEngine, Position, Account, TradeOrder, TradeResult

# 兼容旧导出
from simulator.simulator_engine import SimulatorEngine
from simulator.real_engine import RealEngine

__all__ = [
    # 高层接口
    'BacktestExchangeRunner',
    'Simulator',
    'simulate_mean_cost',
    'simulate_sma',
    'simulate_fixed_amount',

    # 交易所统一接口
    'StockExchange',
    'BacktestExchange',
    'RealtimeSimExchange',
    'LiveExchange',

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
