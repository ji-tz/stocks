# GitHub Actions 工作流（统一文档）

## 位置
`.github/workflows/`

## 触发
- `push` / `pull_request` 到 `main`
- `tag`（发布）

## 四个工作流
- `lint.yml`：Pylint / Flake8 / Mypy（代码静态检查）
- `test.yml`：单元测试 + 集成测试 + 测试日志评论到 PR
- `testgui.yml`：GUI 完整回测报告测试，生成 `testing/` 并将 `testing/guitest.md` 评论到 PR
- `package.yml`：打包产物 + Release（tag）

## 产物
### test.yml
- 测试日志：`test_output.log`
- Artifacts：`test-results`、`test-logs`（保留 30 天）

### testgui.yml
- 截图：`testing/01_open_home.png` 到 `testing/08_backtest_result.png`
- 报告：`testing/guitest.md`
- Artifacts：`guitest-report`（保留 30 天）
- PR 评论：直接读取 `testing/guitest.md` 作为评论正文

### package.yml
- 打包文件（90 天）

## 简图
触发：push / pull_request / tag

Lint + Test + Test GUI + Package（并行）

产物：
- Lint：代码检查报告
- Test：测试日志、测试结果
- Test GUI：完整回测截图、Markdown 报告
- Package：打包文件、Release

## 本地快速验证
- 安装依赖：`requirements.txt`
- 运行测试：`python -m unittest discover tests -v`
- 运行 GUI workflow 契约测试：`python -m unittest tests.test_guitest_workflow_report -v`

## 报告机制（testgui.yml）

`testgui.yml` 现在使用统一报告模式：

1. 运行一次完整 GUI 回测。
2. 在 `testing/` 下生成截图与 `guitest.md`。
3. 上传 `testing/` 为 `guitest-report` artifact。
4. 直接读取 `testing/guitest.md` 更新 PR 评论。
