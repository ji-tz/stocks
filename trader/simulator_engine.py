"""兼容模块：保留旧导入路径 `simulator.simulator_engine.SimulatorEngine`。"""

from exchange.backtest.exchange import BacktestExchange


class SimulatorEngine(BacktestExchange):
    """兼容别名：等价于 `BacktestExchange`。"""
