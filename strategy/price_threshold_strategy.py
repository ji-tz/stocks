"""价格阈值策略（Price Threshold Strategy）

基于预设的买入/卖出价格阈值生成交易信号。当当前价格低于买入阈值时买入，
高于卖出阈值时卖出。支持每日指定执行时间。

核心设计决策说明（PM 评估问题记录）：
────────────────────────────────────────

Q1: 时间条件在回测中的落地方式？
A1: 在 decide() 中通过 date 参数提取小时/分钟，与 decision_hour/decision_minute
    比对。对于不含具体时间的日线 bar（hour=0, minute=0），视为「时间条件自动满足」
    ——触发信号。这是保守选择：日线回测用户通常希望策略在每个 bar 都参与决策，
    而非因缺少时间信息而静默跳过全部 bar。分钟线场景下严格匹配具体时间点。
    实盘场景建议配合外部 cron 调度（当前版本预留接口，未强制实现）。

Q2: buy_threshold 与 sell_threshold 的序关系？
A2: 两者独立，用户可自由配置。典型用法为 buy_threshold < sell_threshold，
    此时两阈值之间形成「持有区间」——价格在该区间内不产生信号。
    若 buy_threshold > sell_threshold 则买入/卖出区间重叠，优先返回 buy 信号
    （代码中按 buy 先判、sell 后判的顺序）。

Q3: 为什么使用 close_price 而非 trade_price？
A3: 阈值比较使用当前 bar 的 close_price（收盘价），这是回测引擎传入的
    标准价格字段。成交价格（trade_price）在回测中由引擎根据 trade_price_field
    配置决定（通常为 open 或 close），策略层不关注成交价，只关注触发信号的价格。
"""

import dataclasses
from typing import Any, Optional

import pandas as pd


AUTO_STRATEGY_SPEC = {
    "key": "price_threshold",
    "label": "价格阈值",
    "runner": "run_module_strategy_backtest",
    "module_interface": True,
    "icon": "🎚️",
    "template": "strategy_config.html",
    "parameters": [
        {
            "name": "buy_threshold",
            "label": "买入阈值",
            "caster": "float",
            "default": 0.0,
            "description": "价格低于此值时触发买入信号。默认 0 表示不启用买入阈值。",
        },
        {
            "name": "sell_threshold",
            "label": "卖出阈值",
            "caster": "float",
            "default": 0.0,
            "description": "价格高于此值时触发卖出信号。默认 0 表示不启用卖出阈值。",
        },
        {
            "name": "decision_hour",
            "label": "执行时(小时)",
            "caster": "int",
            "default": 10,
            "description": "每日策略执行的小时（24小时制，默认10:00）",
        },
        {
            "name": "decision_minute",
            "label": "执行分(分钟)",
            "caster": "int",
            "default": 0,
            "description": "每日策略执行的分钟（默认0分）",
        },
    ],
    "description": "价格阈值策略：价格低于买入阈值时买入，高于卖出阈值时卖出。支持每日指定执行时间。",
    "supported_trade_prices": ["open", "close"],
}


@dataclasses.dataclass
class PriceThresholdDecision:
    """价格阈值策略决策器。

    简单阈值比较（不含持仓状态检查——信号纯由价格驱动）：
    - close_price < buy_threshold  → 'buy'
    - close_price > sell_threshold → 'sell'
    - 否则 → None

    时间过滤：
    - 通过 decision_hour / decision_minute 指定每日执行时间点
    - 接受 bar 的 datetime 中带时间信息（分钟线）或不带（日线）
    - 无时间信息的 bar（hour=0, minute=0）视为时间条件满足，不额外过滤

    This strategy is tick-safe (no lookahead, independent per bar).
    """

    __tick_safe__ = True

    buy_threshold: float = 8.0
    sell_threshold: float = 12.0
    decision_hour: int = 10
    decision_minute: int = 0
    df: Optional[pd.DataFrame] = None

    def _is_decision_time(self, date: Any) -> bool:
        """检查 date 是否匹配决策时间点。

        若 date 无具体时间信息（hour=0, minute=0），视为匹配。
        否则严格比较小时和分钟。
        """
        if date is None:
            return False
        dt = pd.to_datetime(date)
        # 日线模式下 bar 可能不带时间（hour=0, minute=0），视为匹配
        if dt.hour == 0 and dt.minute == 0:
            return True
        return dt.hour == self.decision_hour and dt.minute == self.decision_minute

    def decide(
        self,
        open_price: float,
        close_price: float | None = None,
        avg_cost: float = 0.0,
        shares: float = 0.0,
        date: Any = None,
        **kwargs,
    ) -> Optional[str]:
        """根据价格阈值决定买卖操作。

        Args:
            open_price: 当前 bar 开盘价（未使用）
            close_price: 当前 bar 收盘价，与阈值比较的价格
            avg_cost: 持仓平均成本（未使用）
            shares: 当前持仓数量（未使用，信号纯由价格驱动）
            date: 当前 bar 的日期/时间戳
            **kwargs: 其他参数（未使用）

        Returns:
            'buy' 表示买入，'sell' 表示卖出，None 表示不操作
        """
        _ = open_price, avg_cost, shares, kwargs
        if close_price is None:
            return None
        if not self._is_decision_time(date):
            return None  # 非决策时间点不产生信号

        # 按 buy 先判、sell 后判的顺序
        # 若两阈值重叠则 buy 优先
        if close_price < self.buy_threshold:
            return "buy"
        if close_price > self.sell_threshold:
            return "sell"
        return None


def validate_strategy_parameters(
    buy_threshold: float = 8.0,
    sell_threshold: float = 12.0,
    decision_hour: int = 10,
    decision_minute: int = 0,
    **kwargs,
) -> None:
    """校验价格阈值策略参数。"""
    if buy_threshold <= 0:
        raise ValueError("买入阈值必须大于 0")
    if sell_threshold <= 0:
        raise ValueError("卖出阈值必须大于 0")
    if not (0 <= decision_hour <= 23):
        raise ValueError("执行小时必须在 0~23 之间")
    if not (0 <= decision_minute <= 59):
        raise ValueError("执行分钟必须在 0~59 之间")


def prepare_backtest_data(df: pd.DataFrame, **kwargs) -> pd.DataFrame:
    """价格阈值策略不需要额外技术指标，直接返回原始数据。

    Args:
        df: 原始 OHLCV DataFrame。
        **kwargs: 其他参数（未使用）。

    Returns:
        原样返回输入的 df（接口一致性）。
    """
    return df.copy()


def prepare_backtest_data_for_tick(df_sliding: pd.DataFrame, **kwargs) -> pd.DataFrame:
    """价格阈值策略不需要技术指标，直接返回原始数据（滑动窗口版）。

    Args:
        df_sliding: 滑动窗口 DataFrame。
        **kwargs: 其他参数（未使用）。

    Returns:
        原样返回输入的 df_sliding。
    """
    return df_sliding.copy() if hasattr(df_sliding, "copy") else df_sliding


def create_strategy(
    df: pd.DataFrame,
    buy_threshold: float = 8.0,
    sell_threshold: float = 12.0,
    decision_hour: int = 10,
    decision_minute: int = 0,
    **kwargs,
) -> PriceThresholdDecision:
    """构造价格阈值策略决策器。"""
    return PriceThresholdDecision(
        buy_threshold=buy_threshold,
        sell_threshold=sell_threshold,
        decision_hour=decision_hour,
        decision_minute=decision_minute,
        df=df,
    )
