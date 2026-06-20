"""交易员层 — 时间推进、回测调度、交易信号执行"""

from trader.stocks import (
    init, get_data, get_strategy_spec, list_strategy_specs,
    run_backtest, run_sma_backtest, run_mean_cost, run_fixed_amount,
    run_module_strategy_backtest, run_futures_a50_prev_night, run_signal_template,
    prefetch_for_backtest,
)
from trader.simulator import (
    Simulator, Simulator as BacktestExchangeRunner,
    simulate_sma, simulate_mean_cost, simulate_fixed_amount,
)
from trader.prefetch import (
    prefetch_backtest_data,
    warmup_cache,
    get_or_prefetch,
)

__all__ = [
    "init", "get_data", "get_strategy_spec", "list_strategy_specs",
    "run_backtest", "run_sma_backtest", "run_mean_cost", "run_fixed_amount",
    "run_module_strategy_backtest", "run_futures_a50_prev_night", "run_signal_template",
    "simulate_sma", "simulate_mean_cost", "simulate_fixed_amount",
    "Simulator", "BacktestExchangeRunner",
    "prefetch_backtest_data", "warmup_cache", "get_or_prefetch",
    "prefetch_for_backtest",
]
