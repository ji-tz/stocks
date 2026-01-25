from abc import ABC, abstractmethod
import pandas as pd


class BaseProvider(ABC):
    """抽象数据源提供者，子类实现 `fetch` 方法返回标准 DataFrame。"""

    @abstractmethod
    def fetch(self, symbol: str, start_date: str, end_date: str):
        """从数据源抓取数据，返回包含 ['date','open','high','low','close','volume'] 的 DataFrame。"""
        raise NotImplementedError()
