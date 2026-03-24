# GUI 工作流报告机制

## 当前机制

`testgui.yml` 已经切换为“单次完整回测 + 统一 Markdown 报告”模式。

执行流程：

1. 运行 `tests/guitests/test_gui_backtest_report_e2e.py`
2. 在 `testing/` 下生成 8 张步骤截图
3. 同时生成 `testing/guitest.md`
4. 上传整个 `testing/` 目录为 `guitest-report` artifact
5. 由 `.github/scripts/comment_guitest_report.js` 读取 `testing/guitest.md` 更新 PR 评论

## 调整原因

- 旧方案把截图脚本、回归测试、评论逻辑拆得过散，维护成本高。
- 旧评论链路依赖额外图片上传逻辑，稳定性一般。
- 新方案把“执行真实回测”和“输出可评论报告”合并到一个测试入口，职责更清晰。

## 验证方法

```bash
python -m unittest tests.guitests.test_gui_backtest_report_e2e -v
python -m unittest tests.test_guitest_workflow_report -v
```

验证成功后应看到：

- `testing/01_open_home.png` 到 `testing/08_backtest_result.png`
- `testing/guitest.md`

## 关键文件

- `.github/workflows/testgui.yml`
- `.github/scripts/comment_guitest_report.js`
- `tests/guitests/test_gui_backtest_report_e2e.py`
- `tests/test_guitest_workflow_report.py`

## 参考资料

- [GitHub Actions - github-script](https://github.com/actions/github-script)
- [Data URLs - MDN](https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/Data_URLs)
- [GitHub Markdown Spec](https://github.github.com/gfm/)
- [GitHub API - Issues Comments](https://docs.github.com/en/rest/issues/comments)

## 更新记录

- 2024-02-08：初始版本，修复图片显示问题
