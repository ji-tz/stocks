# Solver 模块 - 策略实现

## 概述

本模块包含各种量化投资策略的实现。每个策略都实现了一个决策器（Decision），用于在模拟交易过程中决定买入、卖出或持有。

## 策略列表

### 1. SMA 策略（简单移动平均策略）
文件：`sma_strategy.py`

**策略逻辑：**
- 当收盘价高于 SMA(period) 时买入
- 当收盘价低于 SMA(period) 时卖出
- 适合趋势跟随交易

**使用方法：**
```python
from simulator.simulator import simulate_sma
from source.data_provider import get_data

# 获取数据
df = get_data(symbol="600900", start_date="20230101", end_date="20231231")

# 运行回测
result = simulate_sma(
    symbol="600900",
    df=df,
    period=20,      # SMA 周期
    lot_size=100,   # 交易手数
    init_cash=100000.0
)
```

说明：SMA 现已完全通过统一模拟器执行，不再依赖独立的第三方回测执行路径。

### 2. 均值成本策略（Mean Cost Strategy）
文件：`mean_cost_strategy.py`

**策略逻辑：**
- 首次买入：持仓为 0 时买入
- 低于成本买入：当价格低于平均成本时继续买入
- 高于成本卖出：当价格高于平均成本时卖出

**使用方法：**
```python
from simulator.simulator import simulate_mean_cost

result = simulate_mean_cost(
    symbol="600900",
    start_date="20230101",
    end_date="20231231",
    lot_size=100,
    init_cash=100000.0
)
```

### 3. 定投策略（Fixed Amount Investment Strategy）
文件：`fixed_amount_strategy.py`

**策略逻辑：**
- 每天投入固定金额购买股票
- 根据当前价格自动计算购买股数（向下取整到 lot_size 的整数倍）
- 只买不卖，持续定投
- 适合长期投资，平滑市场波动

**使用方法：**
```python
from simulator.simulator import simulate_fixed_amount

result = simulate_fixed_amount(
    symbol="600900",
    start_date="20230101",
    end_date="20231231",
    fixed_amount=1000.0,  # 每次投入 1000 元
    lot_size=100,         # 交易手数（100股为1手）
    init_cash=100000.0,   # 初始资金
    verbose=True          # 显示详细日志
)
```

**定投策略的优势：**
- 降低择时风险：不需要判断市场高低点
- 平滑成本：在价格低时买入更多股数，价格高时买入较少股数
- 简单易行：无需复杂的技术分析
- 适合长期投资：通过时间平滑市场波动

### 4. 双均线交叉策略（Dual Moving Average Strategy）
文件：`dual_ma_strategy.py`

**策略逻辑：**
- 短期均线上穿长期均线时买入
- 短期均线下穿长期均线时卖出
- 适合跟随中期趋势

### 5. 布林带策略（Bollinger Bands Strategy）
文件：`bollinger_strategy.py`

**策略逻辑：**
- 收盘价跌破布林带下轨时买入
- 收盘价突破布林带上轨时卖出
- 适合震荡行情中的区间回归

### 6. RSI 策略（RSI Strategy）
文件：`rsi_strategy.py`

**策略逻辑：**
- RSI 低于超卖阈值时买入
- RSI 高于超买阈值时卖出
- 适合低频超跌反弹与回撤止盈场景

### 7. 信号模板策略（Signal Template Strategy）
文件：`signal_template_strategy.py`

**策略逻辑：**
- 通过模板直接配置买入触发条件（价格、指标、均线、量价）
- 通过模板直接配置卖出触发条件（价格、指标、均线、止盈止损）
- 支持买入执行方式：全仓买入 / 固定金额 / 固定仓位
- 支持卖出执行方式：全部卖出 / 固定数量 / 比例卖出
- 支持可选风险控制：止盈、止损

**适用场景：**
- 不想写代码、只想快速组合“条件 + 执行方式”的通用回测
- 用于策略原型验证和信号组合实验

### 8. 价格阈值策略（Price Threshold Strategy）
文件：`price_threshold_strategy.py`

**策略逻辑：**
- 当前价格低于买入阈值（buy_threshold）时买入
- 当前价格高于卖出阈值（sell_threshold）时卖出
- 价格在阈值之间时不操作（持有区间）
- 支持配置每日执行时间（decision_hour / decision_minute）

**可配置参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| buy_threshold | float | 8.0 | 低于此价格时买入（需 > 0） |
| sell_threshold | float | 12.0 | 高于此价格时卖出（需 > 0） |
| decision_hour | int | 10 | 每日执行决策的小时（24小时制） |
| decision_minute | int | 0 | 每日执行决策的分钟 |

**时间过滤说明：**
- 日线回测下，每个 bar 只有一个日期不含具体时间，视为时间条件自动满足
- 分钟线回测下，仅在匹配 decision_hour:decision_minute 的 bar 上执行决策
- 实盘场景可配合外部 cron 按指定时间触发

**边界行为：**
- 价格等于阈值时不会触发（严格小于才买、严格大于才卖）
- 当 buy_threshold > sell_threshold 时（阈值区间重叠），优先返回 buy 信号
- close_price 为 None 时返回 None（无信号）

**使用方法（Python）：**
```python
from trader.stocks import run_module_strategy_backtest

# 执行价格阈值策略回测
result = run_module_strategy_backtest(
    symbol="600900",
    start_date="20230101",
    end_date="20231231",
    strategy_key="price_threshold",
    lot_size=100,
    init_cash=100000.0,
    # 策略参数
    buy_threshold=8.0,
    sell_threshold=12.0,
    decision_hour=10,
    decision_minute=0,
)
```

**使用方法（YAML 配置）：**
```yaml
backtest:
  symbol: "600900"
  start_date: "20230101"
  end_date: "20231231"
  strategy: price_threshold
  lot_size: 100
  init_cash: 100000.0
  params:
    buy_threshold: 8.0
    sell_threshold: 12.0
    decision_hour: 10
    decision_minute: 0
```

**自动注册标识：** `key: "price_threshold"`（参见自动接入章节）

## 策略接口规范

每个策略都应实现 `decide()` 方法：

```python
def decide(self, open_price: float, close_price: float | None = None, 
           avg_cost: float = 0.0, shares: int = 0, date: Any = None):
    """决策是否交易
    
    Args:
        open_price: 开盘价
        close_price: 收盘价
        avg_cost: 平均成本
        shares: 当前持股数
        date: 日期
        
    Returns:
        'buy' - 买入
        'sell' - 卖出
        None - 持有
    """
    pass
```

## 扩展自定义策略

如需添加新策略，请参考以下步骤：

1. 在本目录创建新文件，如 `my_strategy.py`
2. 实现决策类，包含 `decide()` 方法
3. 在策略模块中声明自动注册信息、参数、指标准备和决策构造函数
4. 复用 `simulator/simulator.py` 的统一模拟流程；仅在确有必要时新增专用 runner
5. 在 `tests/` 目录添加测试文件
6. 更新本 README 文档

### 自动接入（重要）

从现在开始，策略支持自动接入，不需要再手工去 `stocks.py` 的注册表里加一条。

约定如下：

1. 策略文件放在 `solver/`，文件名以 `_strategy.py` 结尾。
2. 在策略模块里声明 `AUTO_STRATEGY_SPEC`（字典），至少包含：
   - `key`：策略唯一标识
   - `label`：展示名
   - `runner`：`stocks.py` 中执行函数名（字符串）
   - `module_interface`：是否复用统一模块策略回测入口
3. 参数通过 `parameters` 数组声明，每项包含：
   - `name`、`label`、`caster`（`int|float|str`）、`default`
4. 若 `runner` 为 `run_module_strategy_backtest`，则策略模块还应提供：
   - `validate_strategy_parameters(**params)`：可选，校验参数
   - `prepare_backtest_data(df, **params)`：可选，补充指标列
   - `create_strategy(df, **params)`：必选，返回策略决策对象
5. `stocks.py` 会在构建策略注册表时自动扫描并接入。

示例（简化）：

```python
AUTO_STRATEGY_SPEC = {
    "key": "dual_ma",
    "label": "双均线交叉",
    "runner": "run_module_strategy_backtest",
    "module_interface": True,
    "parameters": [
        {"name": "short_period", "label": "短期均线周期", "caster": "int", "default": 5},
        {"name": "long_period", "label": "长期均线周期", "caster": "int", "default": 20},
    ],
    "supported_trade_prices": ["open"],
}
```

仓库中的 `signal_template_strategy.py` 使用该自动接入机制，并在 GUI 中提供模板化配置界面。

**示例：**
```python
import dataclasses

@dataclasses.dataclass
class MyStrategy:
    param1: float = 1.0
    
    def decide(self, open_price: float, close_price: float | None = None,
               avg_cost: float = 0.0, shares: int = 0, date: Any = None):
        # 实现你的策略逻辑
        if condition:
            return 'buy'
        elif other_condition:
            return 'sell'
        return None
```

## 测试

每个策略都应有对应的测试文件：
- `tests/test_simulator.py` - SMA 和 MeanCost 策略测试
- `tests/test_fixed_amount_strategy.py` - 定投策略测试
- `tests/test_low_frequency_strategies.py` - 双均线、布林带、RSI 策略测试

运行测试：
```bash
# 运行所有策略测试
python -m unittest discover tests -v

# 运行特定策略测试
python -m unittest tests.test_fixed_amount_strategy -v
```

## 回测结果说明

所有策略的回测结果包含以下字段：

| 字段 | 说明 |
|------|------|
| symbol | 股票代码 |
| start_date | 回测开始日期 |
| end_date | 回测结束日期 |
| init_cash | 初始资金 |
| cash | 最终现金 |
| shares | 最终持股数 |
| last_price | 最新价格 |
| market_value | 市值（持股价值） |
| total_value | 总资产（现金 + 市值） |
| realized_pl | 已实现盈亏 |
| unrealized_pl | 未实现盈亏 |
| trades | 交易次数 |
| history | 每日历史记录 |
| trades_list | 交易明细列表 |

## 注意事项

1. **lot_size（交易手数）**：A股市场1手 = 100股，所以 lot_size 通常设为 100
2. **资金不足**：策略决定买入时，如果资金不足，交易会失败
3. **交易时点**：当前统一按开盘价成交，后续若扩展到收盘或盘中，应先在统一注册和模拟入口中增加支持
4. **向后兼容**：修改策略接口时，应保持向后兼容
5. **测试驱动**：新增策略必须先编写测试，确保功能正确

## 相关模块

- `simulator/` - 模拟交易引擎
- `source/` - 数据获取模块
- `tests/` - 测试模块
