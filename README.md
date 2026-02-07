# 量化股票回测系统 Stocks

一个基于 Python 的量化股票回测系统，集成了 Backtrader 策略和 AKShare 数据获取，支持Web界面操作和自动化CI/CD流程。

[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-orange.svg)](.github/workflows/)

## ✨ 特色亮点

- 🚀 **开箱即用**: 提供 Web 界面、命令行工具、Python API 三种使用方式
- 📊 **多数据源**: 支持 AKShare、Baostock 自动切换，数据稳定可靠
- 🎯 **策略灵活**: 内置 SMA、定投策略，支持自定义策略扩展
- 🔍 **详细日志**: verbose 模式提供每日交易明细，便于调试分析
- 🏗️ **架构清晰**: 分层设计，模拟交易引擎与实盘接口解耦，易于扩展
- 🧪 **测试完善**: 单元测试、集成测试、CI/CD 全流程自动化
- 📦 **打包发布**: 支持自动打包和 GitHub Release 发布

## 主要功能

### 1. 量化回测策略
- **SMA策略**: 基于简单移动平均线的交易策略
- **均值成本策略**: 低于成本时买入，高于成本时卖出
- **定投策略**: 每天投入固定金额，自动计算购买股数，适合长期投资

### 2. 数据获取
- 支持 AKShare 和 Baostock 多数据源
- 自动数据缓存和管理
- 灵活的日期范围筛选

### 3. Web界面
- Flask Web应用，提供友好的操作界面
- 可视化回测结果展示
- 支持自定义参数配置
- **历史记录管理**：自动保存最多20条回测记录
- **回测对比功能**：并排对比多个回测记录的收益率、资产曲线等关键指标

### 4. 自动化工作流（CI/CD）

项目采用三个独立的 GitHub Actions 工作流：

- Lint：静态检查（Pylint / Flake8 / Mypy）
- Test：单元测试 + 界面截图 + 集成测试 + PR 评论
- Package：打包产物 + Release（tag）

详情见 [docs/WORKFLOW.md](docs/WORKFLOW.md)。

## 项目结构

```
stocks/
├── main.py                 # 主入口文件
├── stocks.py              # 后端业务模块
├── gui/                   # Web界面
│   ├── web.py            # Flask应用
│   └── templates/        # HTML模板
├── solver/                # 策略实现
│   ├── sma_strategy.py   # SMA策略
│   ├── mean_cost_strategy.py  # 均值成本策略
│   └── fixed_amount_strategy.py  # 定投策略（固定金额）
├── simulator/             # 模拟器
│   └── simulator.py      # 通用模拟器框架
├── source/                # 数据源
│   └── data_provider.py  # 数据提供者
├── tests/                 # 单元测试
│   └── test_yangtze_power.py  # 股票集成测试（支持随机选择）
├── data/                  # 本地数据缓存
├── screenshot_main.py     # 主界面截图脚本
└── .github/
    └── workflows/
        ├── lint.yml       # 代码检视工作流
        ├── test.yml       # 测试工作流
        └── package.yml    # 打包工作流
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
2. **选取策略**：从 SMA、均值成本、定投三种策略中选择
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
from simulator import Simulator
from solver.mean_cost_strategy import MeanCostDecision
import stocks

# 初始化
stocks.init()

# 获取股票数据
data = stocks.get_data(symbol="600900", start_date="20200101")

# 创建模拟器和策略
sim = Simulator(lot_size=100, init_cash=100000.0, verbose=True)
strategy = MeanCostDecision()

# 运行回测
result = sim.simulate(df=data, strategy=strategy, symbol="600900")

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
# 运行所有测试
python -m unittest discover tests -v

# 运行股票集成测试（随机选择）
python -m tests.test_yangtze_power

# 运行股票集成测试（指定股票）
python -c "from tests.test_yangtze_power import run_yangtze_power_test; run_yangtze_power_test(symbol='600900')"
```

### 代码检查

```bash
# Pylint检查
pylint --rcfile=.pylintrc stocks.py main.py

# Flake8检查
flake8 .

# Mypy类型检查
mypy stocks.py main.py --config-file=mypy.ini
```

### 主界面截图

```bash
# 需要先安装playwright浏览器
playwright install chromium

# 运行截图脚本
python screenshot_main.py screenshots/main_gui.png
```

## 命令行工具

### 均值成本策略回测 (run_mean_cost.py)

直接从命令行运行均值成本策略回测：

```bash
# 基本用法（默认：600900长江电力，从2025年1月1日开始）
python run_mean_cost.py

# 自定义参数
python run_mean_cost.py \
  --symbol 600519 \          # 股票代码（贵州茅台）
  --start 20200101 \         # 起始日期
  --lot 100 \                # 每次交易手数
  --cash 100000.0 \          # 初始资金
  --source auto              # 数据源（auto/akshare/baostock）
```

**参数说明：**
- `--symbol, -s`: 股票代码（默认：600900）
- `--start`: 回测起始日期，格式YYYYMMDD（默认：20250101）
- `--lot`: 每次交易手数（默认：100股）
- `--cash`: 初始资金（默认：100000元）
- `--source`: 数据源，可选 auto/akshare/baostock（默认：auto）

**输出示例：**
```python
{'avg_cost': 23.45,
 'cash': 52340.00,
 'realized_pl': 1234.56,
 'shares': 2000,
 'total_value': 99240.00,
 'trades': 20,
 'unrealized_pl': 456.78}
```

### 定投策略（Fixed Amount）使用示例

定投策略每天投入固定金额购买股票，无需择时，适合长期投资：

```python
from simulator.simulator import simulate_fixed_amount

# 运行定投策略回测
result = simulate_fixed_amount(
    symbol="600900",           # 股票代码
    start_date="20230101",     # 开始日期
    end_date="20231231",       # 结束日期
    fixed_amount=1000.0,       # 每次投入 1000 元
    lot_size=100,              # 交易手数（100股为1手）
    init_cash=100000.0,        # 初始资金
    verbose=True               # 显示详细日志
)

# 查看结果
print(f"总交易次数: {result['trades']}")
print(f"最终持仓: {result['shares']} 股")
print(f"总资产: {result['total_value']:.2f} 元")
print(f"收益率: {(result['total_value'] - result['init_cash']) / result['init_cash'] * 100:.2f}%")
```

**定投策略的优势：**
- 🎯 **降低择时风险**：不需要判断市场高低点
- 📊 **平滑成本**：价格低时买入更多，价格高时买入较少
- 💡 **简单易行**：无需复杂的技术分析
- ⏰ **适合长期**：通过时间平滑市场波动

### 演示脚本 (demo_simulator.py)

展示 Simulator 模块的增强功能，包括详细日志、解耦架构等：

```bash
python demo_simulator.py
```

**演示内容：**
1. **Simulator + verbose模式**: 显示每日详细交易日志
2. **直接使用SimulatorEngine**: 展示底层API用法
3. **架构说明**: 展示模块的解耦设计和可扩展性

**特色功能：**
- ✨ 详细的每日交易日志（开盘价、收盘价、操作、持仓、浮盈等）
- 🏗️ 清晰的分层架构（BaseEngine → SimulatorEngine/RealEngine）
- 🔄 向后兼容的高层接口
- 📊 完整的交易报告和统计数据

## GitHub Actions 工作流

项目配置了三个独立的 CI/CD 工作流，分工明确，互不干扰：

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
4. **界面测试** - 主界面自动截图

输出产物：
- 测试截图上传到 Artifacts
- 测试结果 JSON 上传到 Artifacts
- **自动在 PR 中评论测试报告**（包含截图和收益数据）

### 3. 📦 Package 工作流 (`.github/workflows/package.yml`)

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
- **Test**: `contents: write`, `pull-requests: write`（用于提交截图和评论PR）
- **Package**: `contents: write`（用于创建 Release）

## 环境要求

- Python 3.12+
- Node.js (用于Playwright)
- 依赖包见 `requirements.txt`

## 主要依赖

- **backtrader**: 量化回测框架
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

在 `solver/` 目录下创建新的策略类，继承适当的基类并实现 `decide()` 方法：

```python
# solver/my_strategy.py
class MyStrategy:
    def decide(self, row):
        """根据当前行数据决定买入或卖出"""
        # 实现你的策略逻辑
        if 满足买入条件:
            return 'buy'
        elif 满足卖出条件:
            return 'sell'
        return 'hold'
```

然后在测试文件中使用：

```python
from solver.my_strategy import MyStrategy
from simulator import Simulator

sim = Simulator(lot_size=100, init_cash=100000.0)
strategy = MyStrategy()
result = sim.simulate(df=data, strategy=strategy, symbol="600900")
```

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
- [Backtrader](https://www.backtrader.com/) - 量化回测框架
- [AKShare](https://github.com/akfamily/akshare) - 金融数据接口
- [Baostock](http://baostock.com/) - 证券数据平台
- [Flask](https://flask.palletsprojects.com/) - Web 框架
- [Playwright](https://playwright.dev/) - 浏览器自动化
- [Pandas](https://pandas.pydata.org/) - 数据分析库
- [Matplotlib](https://matplotlib.org/) - 数据可视化

感谢所有贡献者的支持！
