# Simulator 模块（精简版）

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
- `simulator/simulator.py`：高层 `Simulator`（向后兼容）

## 关键接口
三种交易所实现接口保持一致，核心方法为：
- `connect()` / `disconnect()`
- `buy(date, price, shares=None)`
- `sell(date, price, shares=None)`
- `get_real_time_price(symbol)`
- `cancel_order(order_id)`

同时保留 `BaseEngine` 的账户查询方法：`get_cash()`、`get_position()`、`get_account()`、`get_total_value()`、`get_summary()`。

## 运行方式
- 推荐使用 `Simulator`：内部封装引擎与策略执行。
- 直接使用 `BacktestExchange` / `RealtimeSimExchange` / `LiveExchange`：按场景手动控制买卖。

## 回测时钟驱动（新功能）
高层回测执行器（`BacktestExchangeRunner`，兼容别名 `Simulator`）在 `mode='backtest'` 下运行。

- 回测模式下，行情推进与策略执行由 `BacktestClock` 驱动：每个 tick 推进一个 bar。
- 返回结果中会包含：`clock_type='backtest'`、`mode='backtest'`。
- 当 `mode` 不是 `backtest` 时，会直接报错，不执行回测循环。

## 日志与报告
`verbose=True` 时输出逐日交易日志与最终汇总报告。

## 仿真粒度与预约单（新功能）
`Simulator.simulate()` 新增以下参数：
- `granularity`：仿真粒度，当前支持 `1d` / `1h`
- `enable_scheduled_orders`：是否启用预约交易

策略可在 `decide()` 中使用 `schedule_order(...)` 下预约单，例如：
```python
def decide(..., schedule_order=None, **kwargs):
  if buy_signal:
    schedule_order(action='sell', after_hours=1, tag='exit_1h')
    return 'buy'
  return None
```

其中：
- `after_bars`：延迟若干个 bar 触发
- `after_hours`：仅 `granularity='1h'` 时可用

预约单会在到期 bar 的开盘价执行。

## T+1 与底仓（新功能）
`Simulator.simulate()` 新增：
- `enforce_t_plus_one`：启用 T+1 卖出约束
- `require_base_position_for_t_plus_one_intraday`：在 T+1 且 `1h` 粒度时强制要求底仓
- `base_position_lots`：底仓手数（当 `require_base_position...=True` 且未传值时，默认 `2` 手）

若开启了 T+1 日内策略且底仓不足，模拟器会直接报错提醒。

## 进度回调支持（新功能）
`Simulator.simulate()` 和相关函数支持 `progress_callback` 参数：
- 回调函数签名：`def callback(current: int, total: int) -> None`
- 在处理每一天数据后调用，报告当前进度
- 用于Web界面实时显示回测进度，避免长时间无响应
- 示例：
  ```python
  def progress_callback(current, total):
      percentage = int(current / total * 100)
      print(f"进度: {percentage}%")
  
  sim = Simulator(lot_size=100, init_cash=100000)
  result = sim.simulate(df=df, strategy=strategy, progress_callback=progress_callback)
  ```

## 返回结果字段
`Simulator.simulate()` 返回包含以下关键字段的字典：
- `max_capital_used`：最大占用资金（初始资金 - 最小现金余额），表示完成策略所需的最低本金
- `min_cash`：最小现金余额，投资过程中现金的最低点
- `total_value`：最终总资产
- `realized_pl`：已实现盈亏
- `unrealized_pl`：未实现盈亏
- `trades`：交易次数
- `history`：每日资产历史记录
- `trades_list`：交易明细列表

## 测试入口
- `tests/test_simulator.py`
- `tests/test_simulator_engine.py`
- `tests/test_backtest_progress.py` - 进度回调测试
- `demo_simulator.py`
