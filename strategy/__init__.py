"""策略层 — 所有策略算法

本模块是策略注册表的核心入口，导出所有策略的决策类和完整元数据。
每个策略的元数据包含：key, name(label), description, icon, template。
"""

from strategy.sma_strategy import SmaDecision
from strategy.mean_cost_strategy import MeanCostDecision
from strategy.fixed_amount_strategy import FixedAmountDecision
from strategy.bollinger_strategy import BollingerDecision
from strategy.dual_ma_strategy import DualMaDecision
from strategy.rsi_strategy import RsiDecision
from strategy.futures_open_hour_strategy import FuturesOpenHourDecision
from strategy.signal_template_strategy import SignalTemplateDecision

# ── 注册表：所有策略的完整元数据 ──────────────────────────────────
# 该注册表被 gui/web.py 和 trader/stocks.py 引用，
# 确保每个新策略在此处注册后即可在 GUI 中动态渲染。
STRATEGY_REGISTRY: dict = {
    "sma": {
        "key": "sma",
        "name": "SMA",
        "description": "基于移动平均线的趋势策略。当价格突破均线时买入，跌破时卖出。",
        "icon": "📈",
        "template": "strategy_dynamic.html",
    },
    "mean_cost": {
        "key": "mean_cost",
        "name": "均值成本",
        "description": "围绕持仓均价进行开盘交易，低买高卖，适合震荡市场。",
        "icon": "💰",
        "template": "strategy_dynamic.html",
    },
    "fixed_amount": {
        "key": "fixed_amount",
        "name": "定投",
        "description": "固定金额定投策略，每天投入固定金额买入股票，平滑市场波动。",
        "icon": "🎯",
        "template": "strategy_dynamic.html",
    },
    "bollinger": {
        "key": "bollinger",
        "name": "布林带",
        "description": "收盘价跌破下轨买入，涨破上轨卖出。基于布林带通道的均值回归策略。",
        "icon": "📉",
        "template": "strategy_dynamic.html",
    },
    "dual_ma": {
        "key": "dual_ma",
        "name": "双均线交叉",
        "description": "短期均线上穿长期均线买入，下穿时卖出。经典趋势跟随策略。",
        "icon": "📉",
        "template": "strategy_dynamic.html",
    },
    "rsi": {
        "key": "rsi",
        "name": "RSI",
        "description": "相对强弱指标策略。RSI 低于超卖阈值买入，高于超买阈值卖出。",
        "icon": "📊",
        "template": "strategy_dynamic.html",
    },
    "a50_prev_night_1h": {
        "key": "a50_prev_night_1h",
        "name": "A50 前夜信号(1h)",
        "description": "根据前一晚 A50 期货涨跌判断次日开盘方向，开盘买入后 1 小时卖出。",
        "icon": "⏰",
        "template": "strategy_dynamic.html",
    },
    "signal_template": {
        "key": "signal_template",
        "name": "信号模板",
        "description": "模板化买卖信号策略：直接配置买入/卖出触发条件、执行方式和止盈止损。",
        "icon": "🔧",
        "template": "strategy_dynamic.html",
    },
}

__all__ = [
    "SmaDecision", "MeanCostDecision", "FixedAmountDecision",
    "BollingerDecision", "DualMaDecision", "RsiDecision",
    "FuturesOpenHourDecision", "SignalTemplateDecision",
    "STRATEGY_REGISTRY",
]
