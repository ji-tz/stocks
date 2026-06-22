"""回测仿真交易所实现。"""

import pandas as pd
from typing import Any

from exchange.simulated_exchange import SimulatedExchangeBase


class BacktestExchange(SimulatedExchangeBase):
    """回测交易所：基于历史数据驱动的仿真撮合。"""

    def __init__(self, init_cash: float = 100000.0, lot_size: float = 100.0,
                 verbose: bool = False, commission_pct: float = 0.00025,
                 stamp_duty_pct: float = 0.001, slippage_pct: float = 0.0,
                 market: str | None = None):
        super().__init__(init_cash=init_cash, lot_size=lot_size, verbose=verbose,
                         commission_pct=commission_pct, stamp_duty_pct=stamp_duty_pct,
                         slippage_pct=slippage_pct, market=market)
        self._current_tick: pd.Series | None = None

    def feed_tick(self, row: pd.Series) -> None:
        """接收并存储当前 tick 的行情数据。

        Args:
            row: 包含 OHLCV 等字段的单行数据。
        """
        self._current_tick = row

    def get_current_state(self) -> dict[str, Any]:
        """返回当前 tick 的完整状态（行情 + 持仓 + 可用资金）。

        Returns:
            包含 'tick'（当前行情行）、'position'（持仓）、'cash'（可用资金）的字典。
            若尚未 feed_tick，则 tick 为 None。
        """
        pos = self.get_position()
        state = {
            "tick": self._current_tick,
            "position": {
                "shares": float(pos.shares),
                "avg_cost": float(pos.avg_cost),
            },
            "cash": float(self.get_cash()),
        }
        return state
