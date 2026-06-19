"""
股票数据预缓存模块 — 用于在用户搜索股票时提前缓存历史数据。

EXCH role owns this module per AGENTS.md.
"""

import logging
from datetime import datetime, timedelta

from exchange.source.data_provider import get_data

logger = logging.getLogger(__name__)


def prefetch_stock_data(symbol: str, years: int = 5) -> dict:
    """
    预取并缓存指定股票的历史日线数据。

    该函数计算起始日期（默认 5 年前），调用 get_data() 获取数据
    （缓存由 get_data 内部处理，保存至 data/{symbol}.csv），
    然后返回操作结果字典。

    Args:
        symbol: 股票代码，例如 '000001'、'00001.HK'、'830799.BJ'
        years:  要获取的历史年数（默认 5 年）

    Returns:
        dict: {
            'success': bool,   — 是否成功获取并缓存
            'rows':    int,    — 缓存的数据行数
            'symbol':  str,    — 股票代码
            'error':   str | None  — 错误信息（成功时为 None）
        }
    """
    today = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=years * 365)).strftime("%Y%m%d")

    try:
        df = get_data(symbol=symbol, start_date=start_date, end_date=today)
        if df is not None and not df.empty:
            row_count = len(df)
            logger.info(
                "成功预缓存 %s 数据，共 %d 行（%s ~ %s）",
                symbol, row_count, start_date, today,
            )
            return {
                "success": True,
                "rows": row_count,
                "symbol": symbol,
                "error": None,
            }
        else:
            logger.warning("预缓存 %s 数据为空", symbol)
            return {
                "success": False,
                "rows": 0,
                "symbol": symbol,
                "error": "无数据返回",
            }
    except Exception as e:
        logger.error("预缓存 %s 失败: %s", symbol, str(e))
        return {
            "success": False,
            "rows": 0,
            "symbol": symbol,
            "error": str(e),
        }
