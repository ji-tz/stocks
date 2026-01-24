# Copilot AI Coding Agent Instructions for stocks

## 项目架构与主要目录
- `main.py`：量化回测主入口，集成 Backtrader 策略与 AKShare 数据获取。
- `gui/`：包含 Web 前端（Flask 实现），如 `gui/web.py`。
- `tests/`：所有单元测试与集成测试，分别测试数据获取与回测主流程。、
- `solver/`：存放回测策略实现，如 `SmaStrategy`。
- `pip.conf`：配置 pip 使用中国镜像源。
- `data/`：存放本地备份的历史数据文件。

## 主要开发模式
- 回测数据通过 AKShare 实时获取，并保留本地备份（于data目录）。
- 回测策略以 Backtrader 框架实现，策略类如 `SmaStrategy` 需在solver中定义和实现。
- Web 界面采用 Flask，入口为 `gui/web.py`，默认监听 127.0.0.1:5000。

## 测试与验证
- 单元测试和集成测试分别位于 `tests/test_main.py` 和 `tests/test_integration.py`。
- 测试用例需覆盖数据获取、回测主流程，所有新功能需配套测试。
- 运行测试命令：
  ```bash
  python -m unittest discover tests
  ```
- 新增的代码必须添加相应测试，确保覆盖率。

## 依赖与环境
- 使用虚拟环境（已自动配置 .venv）。
- 依赖通过 pip 安装，已配置清华镜像。
- 主要依赖：backtrader、akshare、flask、pandas。

## 约定与风格
- 代码、注释、界面均以中文为主。
- 目录结构清晰，功能分层明确：主逻辑、界面、测试分离。
- 新增功能需先写单元测试，集成后写集成测试，所有测试通过后再合并。
- 需采用面向对象思路，模块化设计，确保代码可维护性。
- 采用类型注解，提升代码可读性。

## 典型工作流
1. 在 main.py 或新模块开发功能。
2. 在 tests/ 下添加/更新测试。
3. 本地运行所有测试，确保通过。
4. 如涉及界面，启动 `gui/web.py` 查看效果。

## 参考文件
- `main.py`：量化主流程与策略实现范例。
- `gui/web.py`：Web 界面入口。
- `tests/test_main.py`、`tests/test_integration.py`：测试规范。

## CI/CD
- 使用 GitHub Actions 进行持续集成，自动运行测试。
- 每次提交触发测试，确保主分支代码质量。
- 测试中，使用 GitHub 提供的 Ubuntu 环境，安装依赖并运行测试脚本。
- 截图、录屏并将测试结果上传至 PR 以供审查。

如需扩展新策略、数据源或界面功能，必须遵循现有分层与测试驱动开发模式。
