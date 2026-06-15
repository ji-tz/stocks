"""回测仿真交易所实现。"""

from exchange.simulated_exchange import SimulatedExchangeBase


class BacktestExchange(SimulatedExchangeBase):
    """回测交易所：基于历史数据驱动的仿真撮合。"""
