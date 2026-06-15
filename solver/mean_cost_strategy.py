import dataclasses
from typing import Any

import pandas as pd


AUTO_STRATEGY_SPEC = {
    "key": "mean_cost",
    "label": "均值成本",
    "runner": "run_module_strategy_backtest",
    "module_interface": True,
    "parameters": [],
    "description": "围绕持仓均价进行开盘交易",
    "supported_trade_prices": ["open"],
}


def validate_strategy_parameters(**kwargs) -> None:
    """均值成本策略无额外参数限制。"""
    pass


def prepare_backtest_data(df: pd.DataFrame, **kwargs) -> pd.DataFrame:
    """均值成本策略无需附加指标，直接返回原数据。"""
    return df.copy()


def create_strategy(df: pd.DataFrame, **kwargs) -> 'MeanCostDecision':
    """构造均值成本策略决策器。"""
    return MeanCostDecision()


@dataclasses.dataclass
class MeanCostDecision:
    """决策器：均值成本策略（仅包含决策逻辑）。

    规则：
    - 若持仓为 0：返回 'buy'
    - 否则若开盘价 < 平均成本：返回 'buy'
    - 否则若开盘价 > 平均成本：返回 'sell'
    - 否则返回 None
    """

    def simulate(self, open_price: float, close_price: float | None = None, avg_cost: float = 0.0, shares: float = 0.0, date: Any = None) -> str | None:
        if shares <= 0:
            return 'buy'
        if avg_cost <= 0:
            return None
        if open_price < avg_cost:
            return 'buy'
        if open_price > avg_cost:
            return 'sell'
        return None

    def decide(self, open_price: float, close_price: float | None = None, avg_cost: float = 0.0, shares: float = 0.0, date: Any = None) -> str | None:
        """根据 SMA 信号决定买卖操作（已弃用，请使用 simulate()）。"""
        return self.simulate(open_price=open_price, close_price=close_price, avg_cost=avg_cost, shares=shares, date=date)
