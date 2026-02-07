# GitHub Actions 工作流（统一文档）

## 位置
`.github/workflows/`

## 触发
- `push` / `pull_request` 到 `main`
- `tag`（发布）

## 三个工作流
- `lint.yml`：Pylint / Flake8 / Mypy
- `test.yml`：单元测试 + 界面截图 + 集成测试 + PR 评论
- `package.yml`：打包产物 + Release（tag）

## 产物
- 截图：`screenshots/main_gui.png`
- 集成测试：`test_results/yangtze_power_test.json`
- Artifacts：保留 30/90 天（按工作流）

## 简图
触发：push / pull_request / tag

Lint + Test + Package（并行）

产物：截图、测试结果、打包文件、Release

## 本地快速验证
- 安装依赖：`requirements.txt`
- 运行测试：`python -m unittest discover tests -v`
