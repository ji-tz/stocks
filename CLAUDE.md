# Stocks — Claude Code 项目约定

## 项目概述
| 量化股票回测系统，基于统一模拟交易模型和多数据源，支持 A 股、港股、北证、深证多市场回测，提供 Web 界面操作。

## 技术栈
- Python 3.12+（CI 统一使用 Python 3.12）
- Flask + Bootstrap 4（GUI）
- AKShare / Baostock / EastMoney / Tencent / Sina 等多数据源
- 测试: unittest + Playwright（GUI 端到端测试）
- 代码风格: Flake8 + Pylint + MyPy

## 目录结构
- `exchange/` — 交易所层（多市场数据源、回测/实时仿真/实盘交易引擎、账户模型、交易成本计算）
- `trader/` — 交易员层（回测调度、时间推进、策略执行、模拟盘引擎 Paper Trading）
- `strategy/` — 策略算法（SMA、双均线、布林带、RSI、定投、均值成本、期货开盘策略等）
- `gui/` — Web 界面（Flask 路由 + Jinja2 模板，支持移动端响应式）
- `tests/` — 测试用例（unit/integration/guitests）
- `data/` — 数据缓存

## 核心功能
- **多市场支持**：沪深 A 股、港股（HK）、北证（BJ）、深证（SZ），自动识别市场代码前缀
- **多数据源**：AKShare、Baostock、EastMoney、腾讯、新浪等多源数据获取
- **模拟盘交易**（Paper Trading）：实时仿真运行策略并监控持仓
- **多策略对比回测**：同屏对比多个策略的收益率、回撤、夏普率
- **交易成本模型**：佣金、印花税、滑点差异化配置（港股 T+0、不同手数规则）
- **回测结果导出**：PDF/Excel 格式导出
- **动态策略注册**：新增策略自动注册到首页、路由和模板
- **移动端响应式**：Web 页面适配手机端操作

## 开发规则
1. 所有策略的买卖时机以**开盘价**为成交价
2. 新增策略优先在 `strategy/` 模块中添加，复用统一引擎
3. 参数通过统一注册表管理
4. 代码提交前确保通过 `flake8` 和现有测试
5. 工作流：ARCH 先建 PR → 各角色串行推同一 PR 分支 → LEAD Review → QA 验收后合并
