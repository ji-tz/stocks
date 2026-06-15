"""向后兼容模块。"""
from exchange.simulated_exchange import SimulatedExchangeBase

SimulatedExchange = SimulatedExchangeBase

__all__ = ["SimulatedExchangeBase", "SimulatedExchange"]
