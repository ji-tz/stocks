"""每日收盘反转策略（Close Reversal Strategy）

在每日 15:00 收盘时，根据当日涨跌幅生成反转信号：
- 当日上涨（收盘价 > 前一日收盘价）→ 卖出信号（卖出持仓）
- 当日下跌（收盘价 < 前一日收盘价）→ 买入信号（买入开仓）
- 当日持平（收盘价 == 前一日收盘价）→ 无操作
"""
import dataclasses
from typing import Any, Optional

import pandas as pd


AUTO_STRATEGY_SPEC = {
    "key": "close_reversal",
    "label": "收盘反转",
    "runner": "run_module_strategy_backtest",
    "module_interface": True,
    "icon": "🔁",
    "template": "strategy_config.html",
    "parameters": [
        {
            "name": "min_change_pct",
            "label": "最小变动百分比(%)",
            "caster": "float",
            "default": 0.0,
            "description": "涨跌幅绝对值低于该值时视为持平，不产生信号。例：0.1 表示±0.1%以内视为持平。",
        },
    ],
    "description": "每日收盘反转策略：当日上涨则卖出，当日下跌则买入。基于均值回归逻辑。",
    "supported_trade_prices": ["close"],
}


@dataclasses.dataclass
class CloseReversalDecision:
    """每日收盘反转策略决策器。

    规则：
    - 获取当日收盘价与前一日收盘价，计算涨跌幅。
    - 若涨幅超过 min_change_pct：返回 'sell'（卖出持仓）
    - 若跌幅超过 min_change_pct：返回 'buy'（买入开仓）
    - 若涨跌幅在 ±min_change_pct 范围内：返回 None（无操作）

    该策略是 tick-safe 的（仅依赖当前行与上一行数据）。
    """

    __tick_safe__ = True

    min_change_pct: float = 0.0
    df: Optional[pd.DataFrame] = None
    _date_index_map: dict[str, int] = dataclasses.field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.df is not None and not self.df.empty:
            self.df = self.df.sort_values("date").reset_index(drop=True).copy()
            self._date_index_map = {
                pd.to_datetime(row["date"]).strftime("%Y-%m-%d"): idx
                for idx, row in self.df.iterrows()
            }

    def _get_prev_close(self, date: Any) -> Optional[float]:
        """获取前一交易日的收盘价。"""
        if date is None:
            return None
        key = pd.to_datetime(date).strftime("%Y-%m-%d")
        idx = self._date_index_map.get(key)
        if idx is None or idx <= 0:
            return None
        prev_row = self.df.iloc[idx - 1]
        return float(prev_row["close"])

    def decide(
        self,
        open_price: float,
        close_price: float | None = None,
        avg_cost: float = 0.0,
        shares: float = 0.0,
        date: Any = None,
        **kwargs,
    ) -> Optional[str]:
        _ = open_price, avg_cost, kwargs
        if self.df is None or self.df.empty or date is None:
            return None

        # 获取当日收盘价
        key = pd.to_datetime(date).strftime("%Y-%m-%d")
        idx = self._date_index_map.get(key)
        if idx is None:
            return None
        current_close = float(self.df.iloc[idx]["close"])

        # 获取前一日收盘价
        prev_close = self._get_prev_close(date)
        if prev_close is None or prev_close == 0:
            return None

        # 计算涨跌幅
        daily_return = (current_close - prev_close) / prev_close * 100.0

        # 判断信号
        if daily_return > self.min_change_pct:
            if shares > 0:
                return "sell"
            return None  # 没有持仓时不做卖空
        if daily_return < -self.min_change_pct:
            return "buy"
        # 涨跌幅在阈值范围内，持平
        return None


def validate_strategy_parameters(min_change_pct: float = 0.0, **kwargs) -> None:
    """校验收盘反转策略参数。"""
    if min_change_pct < 0:
        raise ValueError("最小变动百分比不能为负数")


def prepare_backtest_data(df: pd.DataFrame, **kwargs) -> pd.DataFrame:
    """收盘反转策略不需要额外技术指标，直接返回原始数据。

    Args:
        df: 原始 OHLCV DataFrame。
        **kwargs: 其他参数（未使用）。

    Returns:
        原样返回输入的 df（接口一致性）。
    """
    return df.copy()


def prepare_backtest_data_for_tick(df_sliding: pd.DataFrame, **kwargs) -> pd.DataFrame:
    """收盘反转策略不需要技术指标，直接返回原始数据（滑动窗口版）。

    Args:
        df_sliding: 滑动窗口 DataFrame。
        **kwargs: 其他参数（未使用）。

    Returns:
        原样返回输入的 df_sliding。
    """
    return df_sliding.copy() if hasattr(df_sliding, "copy") else df_sliding


def create_strategy(
    df: pd.DataFrame,
    min_change_pct: float = 0.0,
    **kwargs,
) -> CloseReversalDecision:
    """构造收盘反转策略决策器。"""
    return CloseReversalDecision(min_change_pct=min_change_pct, df=df)
