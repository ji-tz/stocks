# Simulator 模块

## 目标

提供统一的股票交易所接口，支持在三种运行形态之间无缝切换：

- 回测仿真（backtest）
- 实时仿真（realtime）
- 实盘交易（live）

## 目录结构

- `simulator/base_engine.py`：抽象接口与数据结构
- `simulator/exchange_interface.py`：股票交易所统一接口（`StockExchange`）
- `simulator/backtest/`：回测仿真实现（`BacktestExchange`）
- `simulator/backtest/clock.py`：回测时钟（`BacktestClock`）
- `simulator/realtime/`：实时仿真实现（`RealtimeSimExchange`）
- `simulator/live/`：实盘交易实现（`LiveExchange`）
- `simulator/simulated_exchange.py`：仿真类实现的公共逻辑
- `simulator/simulator_engine.py`：兼容层（等价 `BacktestExchange`）
- `simulator/real_engine.py`：兼容层（等价 `LiveExchange`）
- `simulator/simulator.py`：高层回测执行器（`BacktestExchangeRunner`，兼容别名 `Simulator`）

## 关键接口

三种交易所实现接口保持一致，核心方法为：

- `connect()` / `disconnect()`
- `buy(date, price, shares=None)`
- `sell(date, price, shares=None)`
- `get_real_time_price(symbol)`
- `cancel_order(order_id)`

同时保留 `BaseEngine` 的账户查询方法：`get_cash()`、`get_position()`、`get_account()`、`get_total_value()`、`get_summary()`。

## 回测时钟驱动

高层回测执行器（`BacktestExchangeRunner`，兼容别名 `Simulator`）在 `mode='backtest'` 下运行。

- 回测模式下，行情推进与策略执行由 `BacktestClock` 驱动：每个 tick 推进一个 bar。
- 返回结果中会包含：`clock_type='backtest'`、`mode='backtest'`。
- 当 `mode` 不是 `backtest` 时，会直接报错，不执行回测循环。

## 进度回调支持

`BacktestExchangeRunner.run()`/`Simulator.simulate()` 和相关便捷函数支持 `progress_callback` 参数：

- 回调函数签名：`def callback(current: int, total: int) -> None`
- 在处理每个 tick 后调用，报告当前进度
- 可用于 Web 界面实时显示回测进度

## 返回结果字段

`Simulator.simulate()` 返回包含以下关键字段：

- `clock_type`、`mode`
- `trade_price_field`、`granularity`
- `max_capital_used`、`min_cash`
- `total_value`、`realized_pl`、`unrealized_pl`
- `trades`、`history`、`trades_list`

## 测试入口

- `tests/test_simulator.py`
- `tests/test_simulator_engine.py`
- `tests/test_backtest_progress.py`
