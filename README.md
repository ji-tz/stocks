# 量化股票回测系统 Stocks

一个基于 Python 的量化股票回测系统，集成了 Backtrader 策略和 AKShare 数据获取，支持Web界面操作和自动化CI/CD流程。

## 主要功能

### 1. 量化回测策略
- **SMA策略**: 基于简单移动平均线的交易策略
- **定投策略**: 均值成本定投策略（Mean Cost Dollar-Cost Averaging）

### 2. 数据获取
- 支持 AKShare 和 Baostock 多数据源
- 自动数据缓存和管理
- 灵活的日期范围筛选

### 3. Web界面
- Flask Web应用，提供友好的操作界面
- 可视化回测结果展示
- 支持自定义参数配置

### 4. 自动化工作流（CI/CD）

项目采用三个独立的 GitHub Actions 工作流，实现全面的 CI/CD 流程：

#### 🔍 Lint 工作流 (lint.yml)
**自动代码检视** - 在每次推送和PR时运行

- **Pylint**: Python代码规范检查
- **Flake8**: 代码风格和语法检查  
- **Mypy**: 静态类型检查

配置文件：
- `.pylintrc`: Pylint配置
- `.flake8`: Flake8配置
- `mypy.ini`: Mypy配置

#### 🧪 Test 工作流 (test.yml)
**自动化测试** - 运行所有测试并生成报告

功能包括：
1. **单元测试**
   - 运行所有 tests/ 目录下的测试
   - 策略模拟器专项测试
   - 验证策略加载功能

2. **界面截图**
   - 使用 Playwright 自动截取主界面
   - 脚本：`screenshot_main.py`

3. **集成测试**
   - 长江电力（600900）定投回测测试
   - 测试期间：2020-2022年
   - 生成收益图表和统计数据

4. **测试报告**
   - 自动上传截图到 Artifacts
   - 上传测试结果 JSON 数据
   - **在 PR 中自动评论测试结果和截图**
   - 提供详细的收益数据摘要

测试输出：
- `screenshots/main_gui.png`: 主界面截图
- `screenshots/yangtze_power_test.png`: 收益图表
- `test_results/yangtze_power_test.json`: 详细测试数据

#### 📦 Package 工作流 (package.yml)
**自动化打包** - 构建发布包和归档产物

打包内容：
1. **源代码包**
   - 完整项目源代码压缩包
   - 自动排除无关文件（.git, __pycache__ 等）

2. **依赖文件**
   - `requirements.txt`: 项目依赖列表
   - `requirements-freeze.txt`: 完整版本锁定

3. **文档**
   - `INSTALL.md`: 详细安装说明
   - `MANIFEST.md`: 打包清单

4. **测试产物**
   - 测试截图归档
   - 测试结果归档

5. **发布支持**
   - 在 tag 推送时自动创建 GitHub Release
   - 附带所有打包文件

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
│   └── mean_cost_strategy.py  # 定投策略
├── simulator/             # 模拟器
│   └── simulator.py      # 通用模拟器框架
├── source/                # 数据源
│   └── data_provider.py  # 数据提供者
├── tests/                 # 单元测试
├── data/                  # 本地数据缓存
├── screenshot_main.py     # 主界面截图脚本
├── test_yangtze_power.py  # 长江电力集成测试
└── .github/
    └── workflows/
        ├── lint.yml       # 代码检视工作流
        ├── test.yml       # 测试工作流
        └── package.yml    # 打包工作流
```

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
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

# 运行长江电力集成测试
python test_yangtze_power.py
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
3. **集成测试** - 长江电力定投回测（2020-2022）
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

## 许可证

[待添加]

## 贡献指南

欢迎提交Issue和Pull Request！
