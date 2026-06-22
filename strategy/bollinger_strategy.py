import dataclasses
from typing import Any, Optional

import pandas as pd


AUTO_STRATEGY_SPEC = {
    "key": "bollinger",
    "label": "布林带",
    "runner": "run_module_strategy_backtest",
    "module_interface": True,
    "icon": "📉",
    "template": "strategy_config.html",
    "parameters": [
        {
            "name": "period",
            "label": "布林带周期",
            "caster": "int",
            "default": 20,
            "description": "移动均线与波动率窗口，默认 20 日",
        },
        {
            "name": "std_multiplier",
            "label": "标准差倍数",
            "caster": "float",
            "default": 2.0,
            "description": "上下轨标准差倍数，默认 2.0",
        },
    ],
    "description": "收盘价跌破下轨买入，涨破上轨卖出",
    "supported_trade_prices": ["open"],
}


@dataclasses.dataclass
class BollingerDecision:
    """布林带低频策略。

    This strategy is tick-safe (works with partial data slices).
    """

    __tick_safe__ = True

    period: int = 20
    std_multiplier: float = 2.0
    df: Optional[pd.DataFrame] = None

    def decide(
        self,
        open_price: float,
        close_price: float | None = None,
        avg_cost: float = 0.0,
        shares: float = 0.0,
        date: Any = None,
    ) -> str | None:
        _ = open_price, avg_cost
        if self.df is None or date is None or close_price is None:
            return None

        rows = self.df[self.df["date"] == date]
        if rows.empty:
            return None

        row = rows.iloc[-1]
        upper = row["bollinger_upper"]
        lower = row["bollinger_lower"]
        if pd.isna(upper) or pd.isna(lower):
            return None

        if shares <= 0 and close_price < lower:
            return "buy"
        if shares > 0 and close_price > upper:
            return "sell"
        return None


def validate_strategy_parameters(period: int = 20, std_multiplier: float = 2.0, **kwargs) -> None:
    """校验布林带策略参数。"""
    if period <= 0:
        raise ValueError('布林带周期必须大于 0')
    if std_multiplier <= 0:
        raise ValueError('标准差倍数必须大于 0')


def prepare_backtest_data(df: pd.DataFrame, period: int = 20, std_multiplier: float = 2.0, **kwargs) -> pd.DataFrame:
    """为布林带策略补充上下轨指标列。

    Uses min_periods=1 so early rows get valid indicators from partial data,
    making this safe for tick-by-tick progression mode.
    """
    prepared = df.copy()
    rolling = prepared["close"].rolling(window=period, min_periods=1)
    prepared["bollinger_mid"] = rolling.mean()
    prepared["bollinger_std"] = rolling.std(ddof=0)  # 使用固定的总体标准差实现，保持当前回测计算结果稳定
    prepared["bollinger_upper"] = prepared["bollinger_mid"] + std_multiplier * prepared["bollinger_std"]
    prepared["bollinger_lower"] = prepared["bollinger_mid"] - std_multiplier * prepared["bollinger_std"]
    return prepared


def prepare_backtest_data_for_tick(df_sliding: pd.DataFrame, period: int = 20,
                                   std_multiplier: float = 2.0, **kwargs) -> pd.DataFrame:
    """为布林带策略补充上下轨指标列（基于滑动窗口计算，确保不偷看未来数据）。

    与 prepare_backtest_data 的区别：
    - 接收的 df_sliding 应当只包含当前 tick 及之前的历史数据。
    - rolling 窗口计算仅基于已有数据，不会引用未来 tick 的信息。

    Args:
        df_sliding: 只包含 0~current_idx 历史数据的 DataFrame。
        period: 布林带窗口周期。
        std_multiplier: 标准差倍数。
        **kwargs: 其他参数（未使用）。

    Returns:
        补充了 bollinger_upper/bollinger_lower 等列的 DataFrame。
    """
    prepared = df_sliding.copy()
    rolling = prepared["close"].rolling(window=period, min_periods=period)
    prepared["bollinger_mid"] = rolling.mean()
    prepared["bollinger_std"] = rolling.std(ddof=0)
    prepared["bollinger_upper"] = prepared["bollinger_mid"] + std_multiplier * prepared["bollinger_std"]
    prepared["bollinger_lower"] = prepared["bollinger_mid"] - std_multiplier * prepared["bollinger_std"]
    return prepared


def create_strategy(df: pd.DataFrame, period: int = 20, std_multiplier: float = 2.0, **kwargs) -> BollingerDecision:
    """构造布林带策略决策器。"""
    return BollingerDecision(period=period, std_multiplier=std_multiplier, df=df)
