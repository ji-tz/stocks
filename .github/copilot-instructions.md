# Copilot AI Coding Agent Instructions for stocks

## 项目大局观
`stocks` 是一个小型量化回测框架，包含：

1. **核心计算库**（`stocks.py` + `solver/` + `simulator/`）
   - 各类策略在 `solver/` 下以独立模块实现，入口函数如 `run_sma_backtest`、`run_mean_cost` 等。
   - `simulator/` 封装交易仿真逻辑，提供 `SimulatorEngine` 等类供策略调用。
   - `stocks.py` 负责统一入口、数据缓存、和对外 API。

2. **数据层**
   - `sources/` 包含多个数据提供者（akshare、baostock），由 `data_provider.py` 统一调度。
   - 本地缓存 CSV 文件存放在 `data/`，测试用例会优先使用这些文件。

3. **Web GUI**（`gui/`）
   - 基于 Flask 的多页面应用，模板位于 `gui/templates`。
   - `gui/web.py` 定义路由和 REST API，大多数页面通过 session 存储中间状态。
   - 前端通过简单的 HTML + JavaScript 实现流程导航、数据验证和实时计算。

4. **测试**
   - 单元/集成测试放在根目录 `tests/`。
   - GUI 端到端测试位于 `tests/guitests/`，使用 Playwright；还有截图脚本供文档和 PR 使用。
   - 测试工具如 `tests/test_utils.py` 提供通用 helper 函数。

5. **运行入口**
   - CLI/脚本入口为 `main.py`，可运行回测、下载数据等。
   - GUI 通过 `python -m gui.web` 启动。

## 开发环境与依赖
- 使用 Python 3.12 虚拟环境（`.venv`）。
- 运行前请执行：
  ```bash
  python -m pip install -r requirements.txt
  python -m playwright install chromium
  python -m playwright install-deps chromium
  ```
  后两步可由测试自动触发（见下文 Playwright 安装逻辑）。
- 使用 `configure_python_environment` / `install_python_packages` 工具管理包，而非手敲 `pip`。

## Playwright & GUI 测试特殊说明
- `tests/guitests/__init__.py` 会在模块导入时检查并自动安装 Chromium 浏览器。
- 截图脚本（`tests/guitests/screenshot_*.py`）同样调用该逻辑以便独立运行。
- GUI 测试通过 `unittest` 直接运行，推荐命令
  ```bash
  python -m unittest tests.guitests.test_time_range_e2e
  python -m unittest tests.guitests.test_gui_workflow_e2e
  ```
  或 `python -m unittest discover` 执行全部。
- 所有 GUI 测试结果需要将截图添加到 PR，CI workflow 会自动存储并显示。
- PR 评论区截图渲染走 GitLab 上传接口（见 `.github/workflows/testgui.yml`）：
   - 需要配置 secrets：`GITLAB_PROJECT_ID`、`GITLAB_TOKEN`
   - 可选 secrets：`GITLAB_API_URL`（默认 `https://gitlab.com/api/v4`）、`GITLAB_BASE_URL`
   - 若未配置 GitLab secrets，workflow 会自动回退为 Artifact 链接，不会阻塞测试通过。

## 典型开发/调试流程
1. 阅读根目录 `README.md` 了解功能和用户操作流。
2. 定位相关模块（`solver`/`gui`/`simulator`等），并阅读对应的 `README.md`。
3. 编写或修改代码；同时更新文档（同级 `README.md`）。
4. 添加或修改测试：单元（`tests/test_*`）、集成（`tests/integration/*`）、以及必要的 GUI 测试。
5. 运行所有测试：
   ```bash
   python -m unittest discover
   ```
   也可使用 `runTests` 工具针对单个文件。
6. 如果涉及 Playwright，请注意首次运行时可能需要下载浏览器（自动完成）。
7. 确保截图脚本可执行并生成图片，便于在 PR 中展示。
8. 提交并附带中文 commit 信息。

## 代码和风格约定
- 所有注释、日志、提交信息使用中文。
- 目录结构层级清晰：计算逻辑 (`solver/`) 与界面 (`gui/`) 严格分离。
- 不增加新模块，若需新增功能尽量在现有模块扩展。
- 使用类型注解，尽量保证 `mypy` 无错误。
- 日志输出使用项目内部工具或直接 `print`，简洁即可。

## 关键文件速览
| 路径 | 说明 |
|------|------|
| `stocks.py` | 回测核心 API；数据缓存与策略调度。 |
| `gui/web.py` | Flask 路由、Session 管理、回测启动逻辑。|
| `gui/templates/*.html` | 页面模板，注意表单字段名称与后端对应。|
| `tests/guitests/*.py` | End‑to‑end GUI 测试和截图脚本。|
| `tests/test_utils.py` | 测试工具，如随机股票选择。|
| `docs/` | 文档目录，包含流程图和测试指南。|

## 其他约定
- 每次修改代码后需同步更新相应的文档文件。
- CI 环境使用 Ubuntu，若本地出现依赖或浏览器问题，可参考 `.github/workflows/testgui.yml`。
- 遵循项目 README 中的“用户操作流”以便 GUI 测试编写。

## 提交与协作
- 使用中文描述提交信息。
- PR 中务必包含测试结果截图，特别是 GUI 端到端用例。遵循 CI 指南，不跳过任何步骤。


> 如有不清楚的地方，请指出需要补充或调整的部分。