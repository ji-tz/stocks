# 探针 PR（用完即删）

用途：验证 workflow-enforcer 的「Issue 关联存在性校验」。

本 PR 的 body 引用 `close #99999`（该 Issue 不存在），预期 `enforce` 必过检查判红。

引用 Issue：#264（分支基于 feat/issue-264-enforce-issue-existence-check）
