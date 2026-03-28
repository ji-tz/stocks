"""回测时钟：驱动历史数据回放与策略执行。"""

from dataclasses import dataclass
from typing import Any, Iterator


@dataclass
class ClockTick:
    """单个时钟刻度。"""

    bar_index: int
    total_bars: int
    timestamp: Any
    row: Any


class BacktestClock:
    """回测时钟。

    按数据行顺序推进，每推进一个 tick，驱动一次“数据更新 + 策略执行”。
    """

    def __init__(self, df, granularity: str = "1d"):
        self.df = df
        self.granularity = granularity
        self._cursor = 0
        self.total_bars = len(df)

    def reset(self) -> None:
        self._cursor = 0

    def iter_ticks(self) -> Iterator[ClockTick]:
        self.reset()
        for idx, (_, row) in enumerate(self.df.iterrows(), start=1):
            self._cursor = idx
            yield ClockTick(
                bar_index=idx,
                total_bars=self.total_bars,
                timestamp=row["date"],
                row=row,
            )
