"""向后兼容模块 — 重新导出新目录结构下的全部公开 API。

原 `simulator` 包已拆分为：
- `exchange/` — 交易所层（base_engine, exchange_interface, simulated_exchange, backtest, live, realtime）
- `trader/` — 交易员层（simulator, simulator_engine, clock, real_engine）
"""

from exchange.base_engine import BaseEngine, Position, Account, TradeOrder, TradeResult
from exchange.exchange_interface import StockExchange
from exchange.backtest.exchange import BacktestExchange
from exchange.realtime.exchange import RealtimeSimExchange
from exchange.live.exchange import LiveExchange

from trader.simulator import BacktestExchangeRunner, Simulator, simulate_fixed_amount, simulate_mean_cost, simulate_sma
from trader.clock import BacktestClock
from trader.simulator_engine import SimulatorEngine

from exchange.real_engine import RealEngine

__all__ = [
    # 高层接口
    "BacktestExchangeRunner",
    "Simulator",
    "simulate_mean_cost",
    "simulate_sma",
    "simulate_fixed_amount",

    # 交易所统一接口
    "StockExchange",
    "BacktestExchange",
    "BacktestClock",
    "RealtimeSimExchange",
    "LiveExchange",

    # 引擎接口
    "BaseEngine",
    "SimulatorEngine",
    "RealEngine",

    # 数据结构
    "Position",
    "Account",
    "TradeOrder",
    "TradeResult",
]
