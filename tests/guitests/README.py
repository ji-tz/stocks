"""GUI 测试说明文档。

此目录下包含端到端测试（使用 Playwright）和截图脚本。

使用指南：

1. 安装依赖

   ```bash
   python -m pip install -r requirements.txt
   ```

2. 第一次运行测试时，Playwright 需要下载浏览器二进制文件。
   为了简化本地开发，我们已在 `tests/guitests/__init__.py` 中
   添加了自动检查逻辑——只要导入任何 guitests 模块，
   就会尝试启动 Chromium。若二进制文件缺失，会自动调用：

   ```bash
   python -m playwright install chromium
   python -m playwright install-deps chromium
   ```

   因此通常无需手动执行上述命令，但如果你的网络环境
   较差，也可以手动运行以节省首次测试时间。

3. 运行端到端测试

   ```bash
   python -m unittest tests.guitests.test_time_range_e2e
   python -m unittest tests.guitests.test_gui_workflow_e2e
   ```

   或者直接运行全部测试：

   ```bash
   python -m unittest discover
   ```

4. 截图脚本

   这些脚本依赖 Playwright 浏览器，执行前会自动进行
   安装检测。可以通过类似以下命令调用：

   ```bash
   python -m tests.guitests.screenshot_time_range
   ```

"""