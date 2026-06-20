"""回测数据预取与缓存预热模块。

该模块为回测流程提供数据预取（prefetch）和缓存预热（cache warming）能力。
利用 EXCH 层已有的 cache-first 机制，在回测开始前主动加载数据到缓存，
从而减少回测时的首次加载延迟。

关键设计：
- 使用 `exchange.source.data_provider.get_data` 作为数据源（已内建 cache-first）
- 使用 `concurrent.futures.ThreadPoolExecutor` 实现并发预热
- 记录缓存命中/未命中状态，便于监控
"""

import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, List

import pandas as pd

from exchange.source.data_provider import get_data as _exchange_get_data

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 内部辅助
# ---------------------------------------------------------------------------


def _check_cache_file(symbol: str, cache_dir: str = "data") -> bool:
    """检查 symbol 的缓存文件是否已存在。

    Args:
        symbol: 股票代码
        cache_dir: 缓存目录（默认 data）

    Returns:
        缓存文件是否存在
    """
    cache_file = os.path.join(cache_dir, f"{symbol}.csv")
    return os.path.isfile(cache_file)


def _normalize_date_str(value: Optional[str]) -> str:
    """将可选的日期字符串规范化为 'YYYYMMDD' 格式。"""
    if value is None:
        return "19700101"
    cleaned = str(value).strip().replace("-", "")
    return cleaned if cleaned else "19700101"


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------


def prefetch_backtest_data(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    source: object = "auto",
) -> pd.DataFrame:
    """预取（prefetch）指定标的的回测数据到缓存。

    直接调用 EXCH 层的 `exchange.source.data_provider.get_data`，该函数
    已内建 cache-first 逻辑。调用后数据会被缓存到 data/{symbol}.csv，
    供后续回测直接使用。

    Args:
        symbol: 股票代码
        start_date: 起始日期（可选，默认全量）
        end_date: 结束日期（可选，默认全量）
        source: 数据源（默认 auto）

    Returns:
        包含 OHLCV 数据的 DataFrame

    Raises:
        传递底层数据源可能抛出的异常
    """
    safe_start = _normalize_date_str(start_date)
    safe_end = _normalize_date_str(end_date)

    logger.info(
        "预取数据: symbol=%s, range=%s~%s, source=%s",
        symbol, safe_start, safe_end, source,
    )

    df = _exchange_get_data(
        symbol=symbol,
        source=source,
        start_date=safe_start,
        end_date=safe_end,
    )

    logger.info(
        "预取完成: symbol=%s, rows=%d, columns=%s",
        symbol, len(df), list(df.columns),
    )
    return df


def warmup_cache(
    symbols: List[str],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    source: object = "auto",
    max_workers: int = 4,
) -> Dict[str, pd.DataFrame]:
    """并发预热多个标的的缓存数据。

    使用 `ThreadPoolExecutor` 并发调用 `prefetch_backtest_data`，
    在回测开始前将数据批量加载到缓存中。

    Args:
        symbols: 股票代码列表
        start_date: 起始日期（可选）
        end_date: 结束日期（可选）
        source: 数据源（默认 auto）
        max_workers: 最大并发数（默认 4）

    Returns:
        字典 {symbol: DataFrame}，按输入顺序排序
    """
    if not symbols:
        logger.warning("warmup_cache 收到空列表，跳过")
        return {}

    logger.info(
        "缓存预热开始: symbols=%d, range=%s~%s, workers=%d",
        len(symbols),
        _normalize_date_str(start_date),
        _normalize_date_str(end_date),
        max_workers,
    )

    results: Dict[str, pd.DataFrame] = {}
    completed = 0
    total = len(symbols)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(
                prefetch_backtest_data, symbol, start_date, end_date, source
            ): symbol
            for symbol in symbols
        }

        for future in as_completed(future_map):
            symbol = future_map[future]
            try:
                df = future.result()
                results[symbol] = df
                completed += 1
                cache_status = "cache_hit" if _check_cache_file(symbol) else "fetched"
                logger.info(
                    "预热 [%d/%d] %s: %s, rows=%d",
                    completed, total, symbol, cache_status, len(df),
                )
            except Exception as exc:
                completed += 1
                logger.error(
                    "预热 [%d/%d] %s 失败: %s",
                    completed, total, symbol, exc,
                )

    logger.info(
        "缓存预热完成: success=%d/%d", len(results), total,
    )

    # 按输入顺序返回
    ordered: Dict[str, pd.DataFrame] = {}
    for symbol in symbols:
        if symbol in results:
            ordered[symbol] = results[symbol]
    return ordered


def get_or_prefetch(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    source: object = "auto",
) -> pd.DataFrame:
    """检查数据是否已缓存，若未缓存则预取。

    便利函数：先检查 data/{symbol}.csv 是否存在。
    - 若已缓存且非空，直接读取并返回（cache hit）
    - 若未缓存或缓存为空，调用 prefetch_backtest_data 获取（cache miss）

    注意：本函数使用 exchange 层的 get_data 读取缓存，其 cache-first 逻辑
    已包含缓存有效性检查。本函数额外增加日志，便于监控缓存命中状态。

    Args:
        symbol: 股票代码
        start_date: 起始日期（可选）
        end_date: 结束日期（可选）
        source: 数据源（默认 auto）

    Returns:
        包含 OHLCV 数据的 DataFrame
    """
    cached = _check_cache_file(symbol)

    if cached:
        logger.info("缓存命中: symbol=%s", symbol)
        # 直接从 exchange 的 cache-first 获取
        safe_start = _normalize_date_str(start_date)
        safe_end = _normalize_date_str(end_date)
        df = _exchange_get_data(
            symbol=symbol,
            source=source,
            start_date=safe_start,
            end_date=safe_end,
        )
        if not df.empty:
            logger.info(
                "缓存命中返回: symbol=%s, rows=%d", symbol, len(df),
            )
            return df
        # 缓存文件存在但数据为空，视为 miss
        logger.warning("缓存文件存在但数据为空: symbol=%s，重新获取", symbol)

    logger.info("缓存未命中: symbol=%s，开始预取", symbol)
    return prefetch_backtest_data(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        source=source,
    )
