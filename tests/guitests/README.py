"""GUI 测试说明文档。

此目录下保留浏览器自动化测试，但不再保留旧的分散截图脚本。

测试组织约定：

- GUI 测试优先验证完整用户流程。
- `test_gui_backtest_report_e2e.py` 是唯一的完整回测报告入口。
- 该测试会把 8 张步骤截图和 `testing/guitest.md` 统一输出到 `testing/`。
- 页面专项测试可以保留，但不再承担 test-gui 主流程产物职责。

使用指南：

1. 安装依赖

   ```bash
   python -m pip install -r requirements.txt
   ```

2. Playwright 浏览器会在导入 `tests.guitests` 时自动检查；若缺失，会自动安装 Chromium。

3. 运行完整 GUI 回测报告测试

   ```bash
   python -m unittest tests.guitests.test_gui_backtest_report_e2e -v
   ```

4. 运行后检查 `testing/`：

   - `01_open_home.png` 到 `08_backtest_result.png`
   - `guitest.md`
"""