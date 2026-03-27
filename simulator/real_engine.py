"""兼容模块：保留旧导入路径 `simulator.real_engine.RealEngine`。"""

from simulator.live.exchange import LiveExchange


class RealEngine(LiveExchange):
    """兼容别名：等价于 `LiveExchange`。"""
