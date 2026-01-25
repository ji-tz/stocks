"""后端业务模块：提供数据导入与策略运行的纯函数接口。

职责：
 - 将与具体业务相关的功能集中到本模块（供测试直接调用）
 - 提供 `init()`、`get_data()`、`run_mean_cost()`、`run_sma_backtest()` 等接口

本模块不启动 Web 服务，仅包含可被 `gui/web.py` 和 `main.py` 调用的函数。
"""
import os
import traceback
from typing import Optional, Dict, Any

from source.data_provider import get_data as _get_data

try:
    from solver.mean_cost_strategy import simulate_mean_cost
except Exception:
    simulate_mean_cost = None


def init(cache_dir: str = "data") -> None:
    """初始化后端（比如创建缓存目录）。"""
    os.makedirs(cache_dir, exist_ok=True)


def get_data(symbol: str = "600900",
             source: object = "auto",
             start_date: Optional[str] = None,
             end_date: Optional[str] = None,
             cache_dir: str = "data",
             max_attempts: int = 3):
    """获取数据，直接调用 `source.data_provider.get_data`。

    该函数是 tests 应该直接调用的入口。
    """
    # 验证并规范日期格式（支持 YYYYMMDD 或 YYYY-MM-DD）
    def _validate_date_str(s: Optional[str]) -> Optional[str]:
        if s is None:
            return None
        s = str(s).strip()
        if s == '':
            return None
        # 支持两种格式
        import re
        if re.fullmatch(r"\d{8}", s):
            return s
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
            return s
        raise ValueError(f"不支持的日期格式: {s}. 请使用 YYYYMMDD 或 YYYY-MM-DD")

    sd = _validate_date_str(start_date)
    ed = _validate_date_str(end_date)

    # 根据 source 做简单规范：
    # - 如果 source 指向或可能使用 akshare（'akshare' 或 'auto'），则把带 '-' 的日期转换为无 '-' 的 YYYYMMDD，方便 akshare 使用
    # - 如果 source 明确为 'baostock'，保持 YYYY-MM-DD 格式
    source_lower = ''
    try:
        if isinstance(source, str):
            source_lower = source.lower()
    except Exception:
        source_lower = ''

    def _normalize_for_source(val: Optional[str]) -> Optional[str]:
        if val is None:
            return None
        # already YYYYMMDD
        if '-' not in val and len(val) == 8:
            return val
        # has hyphens
        if source_lower in ('baostock',):
            # baostock wants YYYY-MM-DD
            return val
        # default to akshare-like format (YYYYMMDD)
        return val.replace('-', '')

    normalized_start = _normalize_for_source(sd)
    normalized_end = _normalize_for_source(ed)

    # 如果没有传入日期参数，则不显式将 start_date/end_date 传给底层，使用底层默认行为（避免传 None 给 provider）
    if sd is None and ed is None:
        df = _get_data(symbol=symbol, source=source, cache_dir=cache_dir, max_attempts=max_attempts)
    else:
        df = _get_data(symbol=symbol, source=source, start_date=normalized_start or start_date, end_date=normalized_end or end_date, cache_dir=cache_dir, max_attempts=max_attempts)

    # 无论底层如何返回（例如从缓存返回整表），在这里对返回的数据按传入的 start/end 进行二次过滤，
    # 以确保前端传入的时间段生效。
    try:
        import pandas as _pd
        if sd is not None or ed is not None:
            df = df.copy()
            if sd is not None:
                sd_dt = _pd.to_datetime(sd)
                df = df[df['date'] >= sd_dt]
            if ed is not None:
                ed_dt = _pd.to_datetime(ed)
                df = df[df['date'] <= ed_dt]
    except Exception:
        # 若过滤过程中出错，不阻塞原始行为，返回原始 df
        pass

    return df


def run_mean_cost(symbol: str = "600900", start_date: Optional[str] = None, end_date: Optional[str] = None,
                  lot_size: int = 100, init_cash: float = 100000.0, source: object = "auto") -> Dict[str, Any]:
    """调用均值成本模拟（封装自 solver.mean_cost_strategy.simulate_mean_cost）。"""
    if simulate_mean_cost is None:
        raise RuntimeError("mean_cost 模块不可用")
    return simulate_mean_cost(symbol=symbol, start_date=start_date, end_date=end_date, lot_size=lot_size, init_cash=init_cash, source=source)


def run_sma_backtest(symbol: str = "600900", source: object = "auto",
                     start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
    """使用 Backtrader 运行 SMA 回测并返回摘要信息（纯数据/数字，不操作 Flask）。

    参数 `start_date` / `end_date` 支持传入字符串以限制回测时间范围。
    如果不传，则使用 `get_data` 的默认范围。
    """
    try:
        import backtrader as bt
        from solver.sma_strategy import SmaStrategy
    except Exception as e:
        raise RuntimeError(f"backtrader 或策略不可用: {e}")

    # 以传入的日期范围优先；若未传则使用 get_data 的默认参数
    if start_date is None and end_date is None:
        df = get_data(symbol=symbol, source=source)
    else:
        df = get_data(symbol=symbol, source=source, start_date=start_date or "19700101", end_date=end_date or "20500101")
    # 只保留回测所需字段
    df = df[["date", "open", "high", "low", "close", "volume"]]

    cerebro = bt.Cerebro()
    data = bt.feeds.PandasData(dataname=df, datetime='date', open='open', high='high', low='low', close='close', volume='volume')
    cerebro.adddata(data)
    cerebro.addstrategy(SmaStrategy)
    cerebro.broker.setcash(100000)
    init_cash = cerebro.broker.getvalue()
    cerebro.run()
    final_cash = cerebro.broker.getvalue()

    return {
        'symbol': symbol,
        'start_date': df['date'].min().strftime('%Y-%m-%d') if not df.empty else '',
        'end_date': df['date'].max().strftime('%Y-%m-%d') if not df.empty else '',
        'init_cash': init_cash,
        'final_cash': final_cash,
    }


if __name__ == '__main__':
    # 方便开发时直接运行并快速检查
    try:
        init()
        print('stocks backend initialized')
    except Exception:
        traceback.print_exc()
