"""
测试工具模块
提供测试中使用的辅助函数，包括随机股票选择
"""
import os
import random
from typing import List, Optional


# A股市场常见股票代码池（用于测试）
# 选择流动性好、数据稳定的大盘蓝筹股
STOCK_POOL: List[str] = [
    "600900",  # 长江电力
    "600519",  # 贵州茅台
    "600036",  # 招商银行
    "601318",  # 中国平安
    "600000",  # 浦发银行
    "601166",  # 兴业银行
    "600016",  # 民生银行
    "601398",  # 工商银行
    "601288",  # 农业银行
    "601988",  # 中国银行
]


def get_random_stock_code(seed: Optional[int] = None, cache_dir: str = "data") -> str:
    """
    从股票池中随机选择一个股票代码
    如果指定了cache_dir，优先从有缓存数据的股票中选择
    
    Args:
        seed: 随机种子，用于可重现的测试。如果为None，则使用真随机
        cache_dir: 缓存目录路径（相对于项目根目录或绝对路径）。
                  如果目录存在，优先从有缓存的股票中选择；
                  如果目录不存在或无缓存文件，则从完整股票池中选择
    
    Returns:
        股票代码字符串
    """
    if seed is not None:
        random.seed(seed)
    
    # 检查是否有缓存目录，如果有，优先从有缓存的股票中选择
    if cache_dir and os.path.isdir(cache_dir):
        cached_stocks = []
        for stock_code in STOCK_POOL:
            cache_file = os.path.join(cache_dir, f"{stock_code}.csv")
            if os.path.exists(cache_file):
                cached_stocks.append(stock_code)
        
        # 如果有缓存的股票，从中随机选择
        if cached_stocks:
            return random.choice(cached_stocks)
    
    # 否则从完整股票池中随机选择
    return random.choice(STOCK_POOL)


def get_stock_pool() -> List[str]:
    """
    返回测试用股票池列表
    
    Returns:
        股票代码列表
    """
    return STOCK_POOL.copy()


def get_cached_stock_codes(cache_dir: str = "data") -> List[str]:
    """
    返回有缓存数据的股票代码列表
    
    Args:
        cache_dir: 缓存目录路径
    
    Returns:
        有缓存数据的股票代码列表
    """
    cached_stocks = []
    if os.path.isdir(cache_dir):
        for stock_code in STOCK_POOL:
            cache_file = os.path.join(cache_dir, f"{stock_code}.csv")
            if os.path.exists(cache_file):
                cached_stocks.append(stock_code)
    return cached_stocks
