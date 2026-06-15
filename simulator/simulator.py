"""向后兼容模块。"""
from trader.simulator import Simulator, BacktestExchangeRunner, simulate_sma, simulate_mean_cost, simulate_fixed_amount, simulate_signal_template, get_data, SUPPORTED_TRADE_PRICE_FIELDS

__all__ = ["Simulator", "BacktestExchangeRunner", "simulate_sma", "simulate_mean_cost", "simulate_fixed_amount", "simulate_signal_template", "get_data", "SUPPORTED_TRADE_PRICE_FIELDS"]
