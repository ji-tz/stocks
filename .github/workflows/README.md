# GitHub Actions 工作流（统一文档）

## 位置
`.github/workflows/`

## 触发
- `push` / `pull_request` 到 `main`
- `tag`（发布）

## 四个工作流
- `lint.yml`：Pylint / Flake8 / Mypy（代码静态检查）
- `test.yml`：单元测试 + 集成测试 + 测试日志评论到PR
- `testgui.yml`：GUI截图测试 + 截图评论到PR（专注于截图和可视化反馈，**图片以 base64 内嵌显示**）
- `package.yml`：打包产物 + Release（tag）

## 产物
### test.yml
- 测试日志：`test_output.log`
- Artifacts：`test-results`、`test-logs`（保留30天）

### testgui.yml
- 截图：`screenshots/main_gui.png`、策略配置截图、历史记录截图、时间段设置截图等
- 集成测试结果：`test_results/yangtze_power_test.json`
- Artifacts：`gui-screenshots`、`gui-test-results`（保留30天）
- **PR评论显示方式**：
  - 小于 500KB 的图片：使用 base64 编码直接嵌入评论中显示
  - 大于 500KB 的图片：显示文件信息和 Artifacts 下载链接

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
- 运行 workflow 图片显示测试：`python -m unittest tests.test_workflow_image_display -v`

## 图片显示机制（testgui.yml）

为了在 PR 评论中正常显示截图，`testgui.yml` 使用以下机制：

1. **小图片（< 500KB）**：转换为 base64 Data URL 直接嵌入 Markdown
   - 优点：图片直接显示在评论中，无需额外点击
   - 缺点：评论内容较大，但仍在 GitHub 限制内（65536字符）
   
2. **大图片（≥ 500KB）**：显示文件信息和下载链接
   - 提供文件名、大小和 Artifacts 下载链接
   - 避免评论内容过大

3. **回退机制**：如果图片不存在或编码失败，显示警告信息

4. **详细日志**：处理过程输出详细日志，便于调试

这种方式解决了 GitHub Markdown 不支持直接显示 artifact 中图片的问题。
