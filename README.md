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

### 4. 自动化工作流

#### 代码静态检查
系统集成了完善的代码质量检查工具：

- **Pylint**: Python代码规范检查
- **Flake8**: 代码风格和语法检查
- **Mypy**: 静态类型检查

配置文件：
- `.pylintrc`: Pylint配置
- `.flake8`: Flake8配置
- `mypy.ini`: Mypy配置

#### 主界面自动截图
使用 Playwright 自动化工具在CI/CD流程中：
- 自动启动 Flask 应用
- 访问主界面并截图
- 将截图上传到 GitHub Actions Artifacts

脚本位置：`screenshot_main.py`

#### 集成测试
**长江电力（600900）定投回测测试**

测试脚本 `test_yangtze_power.py` 提供了完整的定投策略回测：
- 测试期间：2020-2022年
- 策略：定投（Mean Cost DCA）
- 生成详细的收益图表和统计数据
- 自动保存测试结果为JSON格式

测试输出：
- `screenshots/yangtze_power_test.png`: 收益图表
- `test_results/yangtze_power_test.json`: 详细测试数据

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
        └── python-package.yml  # GitHub Actions工作流
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

## GitHub Actions工作流

项目配置了完整的CI/CD流程（`.github/workflows/python-package.yml`），包括：

1. **代码静态检查**
   - Pylint代码规范检查
   - Flake8代码风格检查
   - Mypy类型检查

2. **单元测试**
   - 所有测试用例自动运行
   - 策略模拟器专项测试

3. **主界面截图**
   - 自动启动Flask应用
   - 使用Playwright截取主界面
   - 截图上传到Artifacts

4. **长江电力集成测试**
   - 运行完整的定投策略回测
   - 生成收益图表和统计数据
   - 测试结果上传到Artifacts

5. **PR评论**
   - 自动在Pull Request中发布测试报告
   - 展示测试结果摘要和收益数据
   - 提供Artifacts下载链接

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
