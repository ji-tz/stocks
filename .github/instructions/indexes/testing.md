# testing 目录索引

- testgui 工作流只保留一次完整浏览器回测，不再拆分旧截图脚本。
- 统一入口是 tests/guitests/test_gui_backtest_report_e2e.py。
- 所有截图与测试报告统一输出到 testing/。
- PR 评论内容直接读取 testing/guitest.md。
- 评论脚本位于 .github/scripts/comment_guitest_report.js。