import dataclasses
from typing import Any


@dataclasses.dataclass
class MeanCostDecision:
    """决策器：均值成本策略（仅包含决策逻辑）。

    规则：
    - 若持仓为 0：返回 'buy'
    - 否则若开盘价 < 平均成本：返回 'buy'
    - 否则若开盘价 > 平均成本：返回 'sell'
    - 否则返回 None

    This strategy is tick-safe (works with partial data slices).
    """

    __tick_safe__ = True

    def decide(self, open_price: float, close_price: float | None = None,
               avg_cost: float = 0.0, shares: float = 0.0, date: Any = None) -> str | None:
        if shares <= 0:
            return 'buy'
        if avg_cost <= 0:
            return None
        if open_price < avg_cost:
            return 'buy'
        if open_price > avg_cost:
            return 'sell'
        return None
