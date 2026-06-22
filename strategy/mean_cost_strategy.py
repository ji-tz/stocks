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


def prepare_backtest_data_for_tick(df_sliding, **kwargs):
    """均值成本策略不需要技术指标，直接返回原始数据（接口一致性）。

    Args:
        df_sliding: 滑动窗口 DataFrame。
        **kwargs: 其他参数（未使用）。

    Returns:
        原样返回输入的 df_sliding。
    """
    return df_sliding.copy() if hasattr(df_sliding, 'copy') else df_sliding
