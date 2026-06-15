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
- `solver/` — 策略算法（SMA、双均线、布林带、RSI、定投、均值成本）
- `simulator/` — 统一模拟交易引擎
- `gui/` — Web 界面（Flask）
- `tools/` — 辅助工具
- `tests/` — 测试用例
- `data/` — 数据缓存
- `docs/` — 文档

## 开发规则
1. 所有策略的买卖时机以**开盘价**为成交价
2. 新增策略优先在 `solver/` 模块中添加，复用统一引擎
3. 参数通过统一注册表管理
4. 代码提交前确保通过 `flake8` 和现有测试
