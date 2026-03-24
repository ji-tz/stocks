# testing 目录索引

- testgui 工作流只保留一次完整浏览器回测，不再拆分旧截图脚本。
- 统一入口是 tests/guitests/test_gui_backtest_report_e2e.py。
- Playwright Chromium 的安装检查仅在完整浏览器测试启动前显式执行，避免影响非浏览器 GUI 回归测试；CI 与测试辅助函数统一使用 `playwright install --with-deps chromium` 收敛浏览器和系统依赖安装链路。
- 所有截图与测试报告统一输出到 testing/。
- PR 评论内容直接读取 testing/guitest.md。
- 评论脚本位于 .github/scripts/comment_guitest_report.js。
- tests/test_stocks.py 额外覆盖策略注册表、统一回测请求校验，以及 run_backtest 的分发逻辑。
- tests/test_run_sma.py 与 tests/test_integration.py 已改为验证统一模拟器下的 SMA 结果契约；requirements.txt 与 .github/workflows/test.yml 中也不再安装 backtrader。
- tests/test_data_provider_cache.py 已覆盖 force_refresh 绕过缓存、buffer_days 扩展下载但仍按原始时间段返回的行为；tests/guitests/test_gui_app.py 覆盖 refresh_cache 接口的强制重建参数。
- 本轮架构整理后，应优先保留 tests/test_stocks.py、tests/test_simulator_engine.py、tests/guitests/test_gui_app.py 作为核心回归基线。