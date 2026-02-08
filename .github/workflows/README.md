# GitHub Actions 工作流（统一文档）

## 位置
`.github/workflows/`

## 触发
- `push` / `pull_request` 到 `main`
- `tag`（发布）

## 四个工作流
- `lint.yml`：Pylint / Flake8 / Mypy（代码静态检查）
- `test.yml`：单元测试 + 集成测试 + GUI截图测试 + 测试日志评论到PR
- `testgui.yml`：GUI截图测试 + 截图评论到PR（专注于截图和可视化反馈）
- `package.yml`：打包产物 + Release（tag）

## 产物
### test.yml
- 测试日志：`test_output.log`
- 截图：包括主界面、策略配置、历史记录、股价图表、时间段设置等完整截图
- Artifacts：`test-screenshots`、`test-results`、`test-logs`（保留30天）

### testgui.yml
- 截图：`screenshots/main_gui.png`、策略配置截图、历史记录截图、时间段设置截图等
- 集成测试结果：`test_results/yangtze_power_test.json`
- Artifacts：`gui-screenshots`、`gui-test-results`（保留30天）

### package.yml
- 打包文件（90天）

## 简图
触发：push / pull_request / tag

Lint + Test + Test GUI + Package（并行）

产物：
- Lint：代码检查报告
- Test：测试日志、测试结果
- Test GUI：截图、图表、测试结果JSON
- Package：打包文件、Release

## 本地快速验证
- 安装依赖：`requirements.txt`
- 运行测试：`python -m unittest discover tests -v`
