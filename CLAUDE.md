# Stocks — Claude Code 项目约定

## 项目概述
量化股票回测系统，基于统一模拟交易模型和 AKShare 数据获取，支持 Web 界面操作。

## 技术栈
- Python 3.12+（实际运行在 3.11.14）
- Flask + Bootstrap 4（GUI）
- AKShare / Baostock（数据源）
- 测试: unittest
- 代码风格: Flake8 + Pylint + MyPy

## 目录结构
- `exchange/` — 交易所层（数据源、回测/实时仿真/实盘交易引擎、账户模型）
- `trader/` — 交易员层（回测调度、时间推进、策略执行、模拟盘引擎）
- `strategy/` — 策略算法（SMA、双均线、布林带、RSI、定投、均值成本等）
- `gui/` — Web 界面（Flask 路由 + Jinja2 模板）
- `tests/` — 测试用例（unit/integration/guitests）
- `data/` — 数据缓存

## 开发规则
1. 所有策略的买卖时机以**开盘价**为成交价
2. 新增策略优先在 `strategy/` 模块中添加，复用统一引擎
3. 参数通过统一注册表管理
4. 代码提交前确保通过 `flake8` 和现有测试
