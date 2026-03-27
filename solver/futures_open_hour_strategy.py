import dataclasses
import datetime
from typing import Any, Optional
from source.data_provider import get_data


@dataclasses.dataclass
class FuturesOpenHourDecision:
    """基于富时A50期货涨跌的决策器。

    规则：
    - 在每个交易日开盘前，用提供的期货代码拉取近期日线数据
    - 若期货最近一日收盘价 > 前一日收盘价（即上涨），则返回 'buy'
    - 否则返回 None

    说明：
    - 本策略只负责信号，不直接写死卖出逻辑
    - 若模拟器支持预约单，策略会在买入信号触发时提交“1小时后卖出”预约单
    """

    futures_symbol: str = "FTSE_A50"  # 默认符号，可由调用方传入实际数据源支持的代码
    source: object = "akshare"
    lookback_days: int = 5

    def _is_futures_up(self, date) -> Optional[bool]:
        """判断期货在指定日期（交易日前）的涨跌情况。

        返回 True 表示上涨，False 表示下跌或无上涨，None 表示无法判断（数据不足）。
        """
        try:
            # 请求到 date 之前的若干天数据，确保拿到至少两个有效交易日
            end_date = date.strftime('%Y%m%d')
            start_date = (date - datetime.timedelta(days=max(5, self.lookback_days))).strftime('%Y%m%d')
            df = get_data(symbol=self.futures_symbol, source=self.source,
                          start_date=start_date, end_date=end_date)
            if df is None or df.empty:
                return None
            # 只保留在 date 之前（含）的记录，并按日期排序
            df = df[df['date'] <= date].sort_values('date').reset_index(drop=True)
            if len(df) < 2:
                return None
            last = float(df.iloc[-1]['close'])
            prev = float(df.iloc[-2]['close'])
            return last > prev
        except Exception:
            return None

    def decide(self, open_price: float, close_price: float | None = None, avg_cost: float = 0.0,
               shares: int = 0, date: Any = None, schedule_order=None, **kwargs):
        _ = open_price, close_price, avg_cost, kwargs
        if date is None:
            return None
        is_up = self._is_futures_up(date)
        if is_up is None:
            return None
        if is_up:
            # 只在无持仓时买入（避免重复下单）
            if shares == 0:
                if callable(schedule_order):
                    schedule_order(action='sell', after_hours=1, tag='a50_open_plus_1h_exit')
                return 'buy'
        return None
