# 量化股票回测系统 Stocks

一个基于 Python 的量化股票回测系统，基于统一模拟交易模型和 AKShare 数据获取，支持Web界面操作和自动化CI/CD流程。

[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-orange.svg)](.github/workflows/)

---

## 🧬 项目缘起

本项目是**完全 vibecoding 的产物**——这里没有一个字代码是由人类手工键入的。

### 工具演进

```
本地 GitHub Copilot  →  在线 GitHub Copilot  →  OpenCode  →  OpenClaw  →  Hermes + DeepSeek
（单行补全）           （多文件聊天）            （自主编码 Agent）  （多 Agent 编排）    （完整 AI 团队）
```

每一步演进都是对「AI 到底能帮人类写多少代码」的一次试探。

### 设计理念

**做这个项目有三个目的：**

1. **探索拍脑袋想出来的量化策略到底有没有用**——那些「如果……会怎样」的假设，与其空想，不如跑一下回测验证
2. **探索低成本、高可靠性 vibecoding 的能力边界**——一台树莓派 + 开源模型，到底能支撑多大的 AI 开发管线
3. **技术分享与交流**——把完整的团队架构、工作流设计、工具链演进公开，供同路人参考和讨论

**同时坚决拒绝：**
- ❌ 一站式许愿机式 harness —— 工程师应该理解自己的工具链，而不是在黑盒里许愿
- ❌ 不能保证供应的闭源模型 —— 工具链必须可控，不会被任何一家公司的定价策略绑架
- ❌ 高成本方案 —— 如果 AI 辅助开发比传统开发还贵，那就失去了意义

### 关于这个 AI 团队

本项目使用一套多 Agent 团队架构（定义在 `AGENTS.md` 中）来自动化开发流程。团队成员及分工：

| 角色 | 代号 | 核心职责 |
|------|------|---------|
| 产品经理 | PM | 发现需求、提 Issue、**维护 README** |
| 架构师 | ARCH | 拆解需求、设计模块、定接口 |
| Web 前端 | WEB | UI/UX 设计、Flask 模板、前端交互 |
| **模拟交易所开发工程师** | **EXCH** | 行情数据获取 + 账户管理 + 交易执行 |
| **模拟交易员开发工程师** | **TRADER** | 驱动回测、执行买卖操作 |
| **策略算法工程师** | **STRAT** | 撰写策略逻辑、输出买卖信号 |
| 集成测试 | ITEST | 单元/集成测试、维护 test.yml |
| GUI 测试 | GTEST | Playwright 端到端测试 |
| 研发主管 | LEAD | Review PR、质量把控 |
| 验收测试 | QA | 端到端验收、合并 PR |

整个开发流程由 `Hermes Agent` 调度，通过 GitHub Issues + Pull Requests 驱动：Issue → PM+QA 确认 → ARCH 拆解 → 链式实现 → LEAD Review → QA 验收 → 合并 → 部署。

详见项目根目录的 [`AGENTS.md`](AGENTS.md) —— 那是这份架构的完整手册。

---

## ✨ 特色亮点

- 🚀 **开箱即用**: 提供 Web 界面、命令行工具、Python API 三种使用方式
- 📊 **多数据源**: 支持 AKShare、Baostock 自动切换，数据稳定可靠
- 🎯 **策略灵活**: 内置 SMA、均值成本、定投、双均线、布林带、RSI 等低频策略，支持自定义策略扩展
- 🧩 **统一回测入口**: 通用参数、策略参数和交易时点通过统一请求对象组织，便于扩展新策略
- 🔍 **详细日志**: verbose 模式提供每日交易明细，便于调试分析
- 🏗️ **架构清晰**: 分层设计，模拟交易引擎与实盘接口解耦，易于扩展
- 🧪 **测试完善**: 单元测试、集成测试、CI/CD 全流程自动化
- 📦 **打包发布**: 支持自动打包和 GitHub Release 发布

## 主要功能

### 1. 量化回测策略
- **SMA策略**: 基于简单移动平均线的交易策略
- **均值成本策略**: 低于成本时买入，高于成本时卖出
- **定投策略**: 每天投入固定金额，自动计算购买股数，适合长期投资
- **双均线交叉策略**: 短期均线上穿长期均线买入，下穿卖出
- **布林带策略**: 收盘价跌破下轨买入，突破上轨卖出
- **RSI策略**: RSI 超卖买入、超买卖出

### 回测执行约定
- 当前策略统一以开盘价作为成交时点，先保证现有功能稳定。
- 回测通用参数包括股票、时间范围、初始资金、交易手数、数据源。
- 策略专属参数通过统一注册表管理，例如 `SMA` 的 `period`、定投的 `fixed_amount`。
- 新增策略时，优先在 `strategy/` 模块中补充参数、指标准备和买卖决策逻辑，并复用统一模拟交易流程。

### 2. 数据获取
- 支持 AKShare 和 Baostock 多数据源
- 自动数据缓存和管理
- 灵活的日期范围筛选

### 3. Web界面
- Flask Web应用，提供友好的操作界面
- 可视化回测结果展示
- 支持自定义参数配置

### 4. 自动化工作流（CI/CD）

项目采用四个独立的 GitHub Actions 工作流：

- **Lint**：静态检查（Pylint / Flake8 / Mypy）
- **Test**：运行单元测试、集成测试和GUI截图测试，将测试日志评论到PR中
- **Test GUI**：执行一次完整 GUI 回测，生成 testing 目录产物并将报告评论到 PR 中
- **Package**：打包产物 + Release（tag）

详情见 [.github/workflows/README.md](.github/workflows/README.md)。

## 项目结构

```text
stocks/
├── main.py                 # 主入口文件
├── strategy/               # 策略算法（STRAT角色）
│   ├── sma_strategy.py    # SMA策略
│   ├── mean_cost_strategy.py  # 均值成本策略
│   ├── fixed_amount_strategy.py  # 定投策略
│   ├── dual_ma_strategy.py  # 双均线交叉策略
│   ├── bollinger_strategy.py  # 布林带策略
│   └── rsi_strategy.py   # RSI策略
├── trader/                 # 交易员模块（TRADER角色）
│   ├── simulator.py      # 回测模拟器
│   └── stocks.py         # 业务调度入口
├── exchange/               # 交易所模块（EXCH角色）
│   ├── source/           # 数据源 Provider
│   │   ├── data_provider.py
│   │   ├── akshare_provider.py
│   │   └── baostock_provider.py
│   ├── backtest/         # 回测交易所
│   ├── live/             # 实盘交易所
│   └── realtime/         # 实时仿真
├── gui/                   # Web界面（gui角色）
│   ├── web.py           # Flask应用
│   └── templates/       # HTML模板
├── tests/                 # 测试
│   ├── unit/            # 单元测试（ITEST）
│   ├── integration/     # 集成测试（ITEST）
│   └── guitests/        # GUI E2E测试（GTEST）
├── data/                  # 本地数据缓存
├── testing/               # GUI测试产物
└── .github/
    └── workflows/
        ├── lint.yml
        ├── test.yml
        ├── testgui.yml
        └── package.yml
```

## 快速开始

### 前置要求

- Python 3.12 或更高版本
- pip 包管理器
- （可选）Node.js（用于 Playwright 浏览器自动化）

### 安装步骤

1. **克隆仓库**
   ```bash
   git clone https://github.com/183965983/stocks.git
   cd stocks
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **（可选）安装 Playwright 浏览器**（如需截图功能）
   ```bash
   playwright install chromium
   ```

### 快速开始示例

#### 方式1: 使用 Web 界面

```bash
python main.py
```

然后访问 http://127.0.0.1:5000 即可看到友好的 Web 操作界面。

**Web界面操作流程：**
1. **选取股票**：通过股票代码（如 600900）或股票名称（如 长江电力）搜索
2. **选取策略**：从 SMA、均值成本、定投、双均线、布林带、RSI、期货开仓信号等策略中选择
3. **配置参数**：设置策略参数、初始资金、回测时间范围
4. **查看复盘**：查看回测结果、收益曲线、交易明细

#### 方式2: 使用命令行工具

快速运行定投策略回测：

```bash
# 回测长江电力（600900）从2020年开始的定投策略
python run_mean_cost.py --symbol 600900 --start 20200101 --cash 100000
```

#### 方式3: 使用 Python API

```python
# 初始化
import trader.stocks as stocks
stocks.init()

# 获取股票数据
data = stocks.get_data(symbol="600900", start_date="20200101")

# 使用 stocks.run_backtest() 运行回测
result = stocks.run_backtest(
    symbol="600900",
    start_date="20200101",
    end_date="20231231",
    strategy_key="mean_cost",
    init_cash=100000.0,
)

# 查看结果
print(f"总交易次数: {result['trades']}")
print(f"最终总资产: {result['total_value']:.2f}")
print(f"收益率: {(result['total_value']/100000 - 1)*100:.2f}%")
```

### 运行Web界面

```bash
python main.py
```

访问 http://127.0.0.1:5000 查看主界面

### 运行测试

```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行所有测试
python -m pytest tests/ -v

# 运行单元测试
python -m pytest tests/unit/ -v

# 运行集成测试
python -m pytest tests/integration/ -v

# 运行 GUI E2E 测试
python -m pytest tests/guitests/ -v
```

### 代码检查

```bash
# Pylint检查
pylint --rcfile=.pylintrc main.py trader/ exchange/ strategy/ gui/

# Flake8检查
flake8 .

# Mypy类型检查
mypy main.py --config-file=mypy.ini
```

### GUI 回测报告

```bash
# 运行 GUI E2E 测试
python -m pytest tests/guitests/ -v
```

执行后会在 `testing/` 目录下生成截图和报告。

## GitHub Actions 工作流

定投策略每天投入固定金额购买股票，无需择时，适合长期投资：

```python
import trader.stocks as stocks

# 运行定投策略回测
result = stocks.run_backtest(
    symbol="600900",           # 股票代码
    start_date="20230101",     # 开始日期
    end_date="20231231",       # 结束日期
    strategy_key="fixed_amount",
    strategy_params={"fixed_amount": 1000.0},
    init_cash=100000.0,
)

# 查看结果
print(f"总交易次数: {result['trades']}")
print(f"最终持仓: {result['shares']} 股")
print(f"总资产: {result['total_value']:.2f} 元")
print(f"收益率: {result['total_return_pct']:.2f}%")
```

**定投策略的优势：**
- 🎯 **降低择时风险**：不需要判断市场高低点
- 📊 **平滑成本**：价格低时买入更多，价格高时买入较少
- 💡 **简单易行**：无需复杂的技术分析
- ⏰ **适合长期**：通过时间平滑市场波动

## GitHub Actions 工作流

项目配置了四个独立的 CI/CD 工作流，分工明确，互不干扰：

### 1. 🔍 Lint 工作流 (`.github/workflows/lint.yml`)

**代码质量检查** - 确保代码符合规范

触发条件：
- 推送到 main 分支
- 创建 Pull Request

检查内容：
- **Pylint**: 代码规范检查
- **Flake8**: 代码风格和语法检查
- **Mypy**: 静态类型检查

### 2. 🧪 Test 工作流 (`.github/workflows/test.yml`)

**自动化测试** - 验证功能正确性

触发条件：
- 推送到 main 分支
- 创建 Pull Request

测试内容：
1. **单元测试** - 所有 tests/ 下的测试用例
2. **策略测试** - 交易策略模拟器测试
3. **集成测试** - 股票定投回测（随机选择，2020-2022）

输出产物：
- 测试结果 JSON 上传到 Artifacts
- **自动在 PR 中评论测试报告**（包含测试日志）

### 3. 🖼️ Test GUI 工作流 (`.github/workflows/testgui.yml`)

**GUI 完整回测报告测试** - 专注于一次真实回测和统一报告产物

触发条件：
- 推送到 main 分支
- 创建 Pull Request

测试内容：
1. **完整 GUI 主流程** - 从首页到结果页完成一次真实回测
2. **testing 截图产物** - 固定输出 8 张步骤截图
3. **Markdown 报告产物** - 生成 `testing/guitest.md`
4. **PR 评论同步** - 直接读取 `testing/guitest.md` 更新 PR 评论

输出产物：
- `testing/` 目录上传到 Artifacts（保留30天）
- **自动在 PR 中评论 GUI 测试报告**（内容来自 `testing/guitest.md`）

### 4. 📦 Package 工作流 (`.github/workflows/package.yml`)

**打包和发布** - 构建发布包

触发条件：
- 推送到 main 分支
- 创建 Pull Request
- 推送 tag（如 v1.0.0）
- 手动触发

打包内容：
- 源代码压缩包（排除无关文件）
- 依赖列表（requirements.txt 和完整版本锁定）
- 安装说明文档（INSTALL.md）
- 打包清单（MANIFEST.md）
- 测试产物归档

特殊功能：
- **在 tag 推送时自动创建 GitHub Release**
- 包含所有发布文件和说明

### 工作流权限

- **Lint**: 无需特殊权限
- **Test**: `contents: write`, `pull-requests: write`（用于评论测试日志到PR）
- **Test GUI**: `contents: read`, `pull-requests: write`, `issues: write`（用于评论 GUI 报告到 PR）
- **Package**: `contents: write`（用于创建 Release）

## 环境要求

- Python 3.12+
- Node.js (用于Playwright)
- 依赖包见 `requirements.txt`

## 主要依赖

- **统一模拟器**: 回测执行核心，负责策略驱动和成交撮合
- **akshare/baostock**: 股票数据源
- **pandas**: 数据处理
- **matplotlib**: 图表生成
- **Flask**: Web框架
- **playwright**: 浏览器自动化
- **pylint/flake8/mypy**: 代码质量工具

## 开发约定

- 代码、注释、界面均使用中文
- 遵循模块化设计原则
- 新功能需配套单元测试
- 采用类型注解提升代码可读性
- 使用面向对象设计模式

## 测试驱动开发

所有新功能开发遵循TDD流程：
1. 编写单元测试
2. 实现功能代码
3. 运行测试确保通过
4. 编写集成测试
5. 代码审查和优化

## 常见问题 (FAQ)

### Q1: 如何添加新的交易策略？

在 `strategy/` 目录下创建新的策略类，实现 `prepare_backtest_data()` 和 `simulate()` 方法：

```python
# strategy/my_strategy.py
class MyStrategy:
    @staticmethod
    def prepare_backtest_data(df, **params):
        # 计算技术指标
        return df

    @staticmethod
    def simulate(df, position, **params):
        # 输出 buy/sell/None 信号
        return {'signal': 'buy' if ... else 'sell'}
```

然后在策略注册表中注册（`strategy/__init__.py`），Web 界面会自动出现配置页面。

### Q2: 支持哪些数据源？

当前支持两个主要数据源：
- **AKShare**: 国内股票数据，更新及时
- **Baostock**: 历史数据完整，稳定性好

使用 `source="auto"` 会自动选择可用的数据源，优先使用 AKShare。

### Q3: 如何调试策略？

使用 `verbose=True` 参数开启详细日志：

```python
sim = Simulator(lot_size=100, init_cash=100000.0, verbose=True)
result = sim.simulate(df=data, strategy=strategy, verbose=True)
```

这会打印每日的详细交易信息，包括价格、操作、持仓、浮盈等。

### Q4: CI/CD 工作流失败怎么办？

1. **Lint失败**: 查看 Pylint/Flake8/Mypy 的错误信息，修复代码规范问题
2. **Test失败**: 查看测试日志，确定失败的测试用例，本地复现并修复
3. **截图失败**: 检查 Playwright 安装，确保 Flask 应用能正常启动

查看 [.github/workflows/](/.github/workflows/) 下的工作流配置文件了解详情。

### Q5: 如何贡献代码？

请参考下方的"贡献指南"章节。

## 贡献指南

欢迎提交 Issue 和 Pull Request！我们非常感谢社区的贡献。

### 贡献流程

1. **Fork 本仓库**
   ```bash
   # 在 GitHub 上点击 Fork 按钮
   ```

2. **克隆到本地**
   ```bash
   git clone https://github.com/你的用户名/stocks.git
   cd stocks
   ```

3. **创建功能分支**
   ```bash
   git checkout -b feature/your-feature-name
   ```

4. **安装开发依赖**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

5. **进行开发**
   - 编写代码
   - 添加/更新测试
   - 确保测试通过
   - 运行代码检查

6. **运行测试和检查**
   ```bash
   # 运行所有测试
   python -m unittest discover tests -v
   
   # 代码检查
   pylint --rcfile=.pylintrc stocks.py main.py
   flake8 .
   mypy stocks.py main.py --config-file=mypy.ini
   ```

7. **提交更改**
   ```bash
   git add .
   git commit -m "描述你的更改"
   ```

8. **推送到 GitHub**
   ```bash
   git push origin feature/your-feature-name
   ```

9. **创建 Pull Request**
   - 在 GitHub 上打开你的 Fork
   - 点击 "New Pull Request"
   - 填写 PR 描述，说明你的更改
   - 等待 CI/CD 自动测试通过
   - 等待代码审查

### 开发规范

- **代码风格**: 遵循 PEP 8，使用 Pylint/Flake8 检查
- **类型注解**: 尽可能添加类型注解，使用 Mypy 检查
- **测试驱动**: 新功能需要配套单元测试
- **中文注释**: 代码、注释、文档均使用中文
- **模块化**: 保持代码模块化，单一职责原则
- **向后兼容**: 尽量保持向后兼容性

### 报告问题

发现 Bug 或有功能建议？请创建 Issue：

1. 使用清晰的标题
2. 详细描述问题或建议
3. 提供复现步骤（如果是 Bug）
4. 提供环境信息（Python版本、操作系统等）
5. 如果可能，提供最小可复现示例

## 许可证

本项目采用 **MIT License** 开源许可证。

这意味着你可以自由地：
- ✅ 使用本项目进行商业和非商业用途
- ✅ 修改源代码
- ✅ 分发原始或修改后的代码
- ✅ 私有使用

唯一的要求是：
- 📝 保留原始的版权声明和许可证文本

详见 [LICENSE](LICENSE) 文件（如果存在）。

**免责声明**: 本项目仅供学习和研究使用，不构成任何投资建议。股市有风险，投资需谨慎。

## 相关链接

- 📖 [Simulator 架构文档](docs/SIMULATOR_ARCHITECTURE.md)
- 🔄 [工作流详细说明](docs/WORKFLOW.md)
- 🐛 [提交 Issue](https://github.com/183965983/stocks/issues)
- 🔀 [提交 Pull Request](https://github.com/183965983/stocks/pulls)

## 致谢

本项目使用了以下优秀的开源项目：
- [AKShare](https://github.com/akfamily/akshare) - 金融数据接口
- [Baostock](http://baostock.com/) - 证券数据平台
- [Flask](https://flask.palletsprojects.com/) - Web 框架
- [Playwright](https://playwright.dev/) - 浏览器自动化
- [Pandas](https://pandas.pydata.org/) - 数据分析库
- [Matplotlib](https://matplotlib.org/) - 数据可视化

感谢所有贡献者的支持！
