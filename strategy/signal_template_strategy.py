import dataclasses
import math
from typing import Any, Optional

import pandas as pd


AUTO_STRATEGY_SPEC = {
    "key": "signal_template",
    "label": "信号模板",
    "runner": "run_signal_template",
    "icon": "🔧",
    "template": "strategy_config.html",
    "parameters": [
        {
            "name": "buy_trigger",
            "label": "买入触发条件",
            "caster": "str",
            "default": "price_below",
            "description": "可选：价格条件/指标条件/均线条件/量价条件",
        },
        {
            "name": "buy_price_value",
            "label": "买入价格阈值(元)",
            "caster": "float",
            "default": 0.0,
            "description": "当买入条件为价格触发时生效",
        },
        {
            "name": "buy_exec_mode",
            "label": "买入执行方式",
            "caster": "str",
            "default": "all_in",
            "description": "all_in/fixed_amount/fixed_position",
        },
        {
            "name": "buy_fixed_amount",
            "label": "固定金额买入(元)",
            "caster": "float",
            "default": 10000.0,
            "description": "买入执行方式为固定金额时生效",
        },
        {
            "name": "buy_position_pct",
            "label": "固定仓位买入(%)",
            "caster": "float",
            "default": 30.0,
            "description": "买入执行方式为固定仓位时生效",
        },
        {
            "name": "take_profit_pct",
            "label": "止盈阈值(%)",
            "caster": "float",
            "default": 0.0,
            "description": "大于0时启用止盈",
        },
        {
            "name": "stop_loss_pct",
            "label": "止损阈值(%)",
            "caster": "float",
            "default": 0.0,
            "description": "大于0时启用止损",
        },
        {
            "name": "sell_trigger",
            "label": "卖出触发条件",
            "caster": "str",
            "default": "price_above",
            "description": "可选：价格条件/指标条件/均线条件/止盈止损",
        },
        {
            "name": "sell_price_value",
            "label": "卖出价格阈值(元)",
            "caster": "float",
            "default": 0.0,
            "description": "当卖出条件为价格触发时生效",
        },
        {
            "name": "sell_profit_pct",
            "label": "卖出止盈阈值(%)",
            "caster": "float",
            "default": 0.0,
            "description": "当卖出触发条件为盈利阈值时生效",
        },
        {
            "name": "sell_loss_pct",
            "label": "卖出止损阈值(%)",
            "caster": "float",
            "default": 0.0,
            "description": "当卖出触发条件为亏损阈值时生效",
        },
        {
            "name": "sell_exec_mode",
            "label": "卖出执行方式",
            "caster": "str",
            "default": "all",
            "description": "all/fixed_shares/ratio",
        },
        {
            "name": "sell_fixed_shares",
            "label": "固定卖出数量(股)",
            "caster": "float",
            "default": 100.0,
            "description": "卖出执行方式为固定数量时生效",
        },
        {
            "name": "sell_ratio_pct",
            "label": "卖出比例(%)",
            "caster": "float",
            "default": 50.0,
            "description": "卖出执行方式为比例时生效",
        },
    ],
    "description": "模板化买卖信号策略：直接配置买入/卖出触发条件、执行方式和止盈止损。",
    "supported_trade_prices": ["open", "close"],
}


@dataclasses.dataclass
class SignalTemplateDecision:
    """模板化信号策略决策器。"""

    df: pd.DataFrame
    lot_size: float
    buy_trigger: str = "price_below"
    buy_price_value: float = 0.0
    buy_exec_mode: str = "all_in"
    buy_fixed_amount: float = 10000.0
    buy_position_pct: float = 30.0
    take_profit_pct: float = 0.0
    stop_loss_pct: float = 0.0
    sell_trigger: str = "price_above"
    sell_price_value: float = 0.0
    sell_profit_pct: float = 0.0
    sell_loss_pct: float = 0.0
    sell_exec_mode: str = "all"
    sell_fixed_shares: float = 100.0
    sell_ratio_pct: float = 50.0
    _date_index_map: dict[str, int] = dataclasses.field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        self.df = self.df.sort_values("date").reset_index(drop=True).copy()
        self._date_index_map = {
            pd.to_datetime(row["date"]).strftime("%Y-%m-%d"): idx
            for idx, row in self.df.iterrows()
        }

    @staticmethod
    def build_features(df: pd.DataFrame) -> pd.DataFrame:
        """构建策略所需技术指标。"""
        work = df.sort_values("date").reset_index(drop=True).copy()

        work["ma5"] = work["close"].rolling(window=5, min_periods=1).mean()
        work["ma20"] = work["close"].rolling(window=20, min_periods=1).mean()
        work["vol_ma5"] = work["volume"].rolling(window=5, min_periods=1).mean()

        delta = work["close"].diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.rolling(window=14, min_periods=14).mean()
        avg_loss = loss.rolling(window=14, min_periods=14).mean()
        rs = avg_gain / avg_loss.replace(0, pd.NA)
        work["rsi14"] = 100 - (100 / (1 + rs))
        work["rsi14"] = work["rsi14"].fillna(50.0)

        ema12 = work["close"].ewm(span=12, adjust=False).mean()
        ema26 = work["close"].ewm(span=26, adjust=False).mean()
        work["macd_diff"] = ema12 - ema26
        work["macd_dea"] = work["macd_diff"].ewm(span=9, adjust=False).mean()

        low_min = work["low"].rolling(window=9, min_periods=1).min()
        high_max = work["high"].rolling(window=9, min_periods=1).max()
        rsv = (work["close"] - low_min) / (high_max - low_min).replace(0, pd.NA) * 100
        work["k"] = rsv.ewm(com=2, adjust=False).mean().fillna(50.0)
        work["d"] = work["k"].ewm(com=2, adjust=False).mean().fillna(50.0)

        return work

    def _get_row(self, date: Any) -> Optional[pd.Series]:
        if date is None:
            return None
        key = pd.to_datetime(date).strftime("%Y-%m-%d")
        idx = self._date_index_map.get(key)
        if idx is None:
            return None
        return self.df.iloc[idx]

    def _get_prev_row(self, date: Any) -> Optional[pd.Series]:
        if date is None:
            return None
        key = pd.to_datetime(date).strftime("%Y-%m-%d")
        idx = self._date_index_map.get(key)
        if idx is None or idx <= 0:
            return None
        return self.df.iloc[idx - 1]

    def _round_to_lot(self, shares: float) -> float:
        if self.lot_size <= 0:
            return 0.0
        lots = math.floor((float(shares) + 1e-12) / self.lot_size)
        return round(lots * self.lot_size, 6)

    def _is_buy_signal(self, row: pd.Series, prev_row: Optional[pd.Series], price: float) -> bool:
        trigger = self.buy_trigger
        if trigger == "price_below":
            return self.buy_price_value > 0 and price <= self.buy_price_value
        if trigger == "price_above":
            return self.buy_price_value > 0 and price >= self.buy_price_value
        if trigger == "macd_golden" and prev_row is not None:
            return prev_row["macd_diff"] <= prev_row["macd_dea"] and row["macd_diff"] > row["macd_dea"]
        if trigger == "kdj_golden" and prev_row is not None:
            return prev_row["k"] <= prev_row["d"] and row["k"] > row["d"]
        if trigger == "rsi_oversold":
            return row["rsi14"] <= 30
        if trigger == "ma_above_5":
            return row["close"] >= row["ma5"]
        if trigger == "ma_above_20":
            return row["close"] >= row["ma20"]
        if trigger == "volume_rise":
            return row["close"] > row["open"] and row["volume"] > row["vol_ma5"]
        if trigger == "volume_pullback":
            return row["close"] < row["open"] and row["volume"] < row["vol_ma5"]
        return False

    def _is_sell_signal(self, row: pd.Series, prev_row: Optional[pd.Series], price: float, avg_cost: float) -> bool:
        trigger = self.sell_trigger
        pnl_pct = 0.0
        if avg_cost > 0:
            pnl_pct = (price - avg_cost) / avg_cost * 100.0

        if self.take_profit_pct > 0 and pnl_pct >= self.take_profit_pct:
            return True
        if self.stop_loss_pct > 0 and pnl_pct <= -abs(self.stop_loss_pct):
            return True

        if trigger == "price_above":
            return self.sell_price_value > 0 and price >= self.sell_price_value
        if trigger == "price_below":
            return self.sell_price_value > 0 and price <= self.sell_price_value
        if trigger == "macd_dead" and prev_row is not None:
            return prev_row["macd_diff"] >= prev_row["macd_dea"] and row["macd_diff"] < row["macd_dea"]
        if trigger == "kdj_dead" and prev_row is not None:
            return prev_row["k"] >= prev_row["d"] and row["k"] < row["d"]
        if trigger == "rsi_overbought":
            return row["rsi14"] >= 70
        if trigger == "ma_below_5":
            return row["close"] <= row["ma5"]
        if trigger == "ma_below_20":
            return row["close"] <= row["ma20"]
        if trigger == "profit_target":
            return self.sell_profit_pct > 0 and pnl_pct >= self.sell_profit_pct
        if trigger == "loss_limit":
            return self.sell_loss_pct > 0 and pnl_pct <= -abs(self.sell_loss_pct)
        return False

    def _compute_buy_shares(self, price: float, cash: float) -> float:
        if price <= 0 or cash <= 0:
            return 0.0

        mode = self.buy_exec_mode
        if mode == "all_in":
            return self._round_to_lot(cash / price)
        if mode == "fixed_amount":
            amount = max(self.buy_fixed_amount, 0.0)
            return self._round_to_lot(min(amount, cash) / price)
        if mode == "fixed_position":
            pct = max(min(self.buy_position_pct, 100.0), 0.0) / 100.0
            return self._round_to_lot((cash * pct) / price)
        return 0.0

    def _compute_sell_shares(self, position_shares: float) -> float:
        mode = self.sell_exec_mode
        if position_shares <= 0:
            return 0.0
        if mode == "all":
            return self._round_to_lot(position_shares)
        if mode == "fixed_shares":
            return self._round_to_lot(min(self.sell_fixed_shares, position_shares))
        if mode == "ratio":
            pct = max(min(self.sell_ratio_pct, 100.0), 0.0) / 100.0
            return self._round_to_lot(position_shares * pct)
        return 0.0

    def decide(
        self,
        open_price: float,
        close_price: float,
        avg_cost: float = 0.0,
        shares: float = 0.0,
        date: Any = None,
        cash: float = 0.0,
        trade_price: float | None = None,
        **kwargs,
    ):
        _ = kwargs, open_price
        row = self._get_row(date)
        if row is None:
            return None
        prev_row = self._get_prev_row(date)

        price = float(trade_price) if trade_price is not None else float(close_price)
        position_shares = float(shares)

        if position_shares > 0 and self._is_sell_signal(
                row=row, prev_row=prev_row, price=price, avg_cost=float(avg_cost)):
            sell_shares = self._compute_sell_shares(position_shares=position_shares)
            if sell_shares > 0:
                return {"action": "sell", "shares": sell_shares}

        if position_shares <= 0 and self._is_buy_signal(row=row, prev_row=prev_row, price=price):
            buy_shares = self._compute_buy_shares(price=price, cash=float(cash))
            if buy_shares > 0:
                return {"action": "buy", "shares": buy_shares}

        return None
