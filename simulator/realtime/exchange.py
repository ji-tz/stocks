"""实时仿真交易所实现。"""

from simulator.simulated_exchange import SimulatedExchangeBase


class RealtimeSimExchange(SimulatedExchangeBase):
    """实时仿真交易所：接口与回测、实盘一致，便于无缝切换。"""
