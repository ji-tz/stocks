"""向后兼容模块 — 重新导出新位置。"""
from exchange.backtest.exchange import BacktestExchange
from trader.clock import BacktestClock

__all__ = ["BacktestExchange", "BacktestClock"]
