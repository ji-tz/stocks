# Simulator 模块（精简版）

## 目标
提供统一的交易引擎接口，支持模拟交易并为实盘扩展预留。

## 目录结构
- `simulator/base_engine.py`：抽象接口与数据结构
- `simulator/simulator_engine.py`：内存模拟引擎
- `simulator/real_engine.py`：实盘接口占位
- `simulator/simulator.py`：高层 `Simulator`（向后兼容）

## 关键接口
`BaseEngine` 统一约定：`buy()`、`sell()`、`get_cash()`、`get_position()`、`get_account()`、`get_total_value()`、`get_summary()`。

## 运行方式
- 推荐使用 `Simulator`：内部封装引擎与策略执行。
- 直接使用 `SimulatorEngine`：手动控制买卖。

## 日志与报告
`verbose=True` 时输出逐日交易日志与最终汇总报告。

## 测试入口
- `tests/test_simulator.py`
- `tests/test_simulator_engine.py`
- `demo_simulator.py`
