#!/usr/bin/env bash
# workflow-enforcer — 检查 PR body 中的 ARCH 拆解方案
set -euo pipefail

PR_BODY="$1"

if [ -z "$PR_BODY" ]; then
  echo "⚠ PR body 为空"
  exit 0
fi

CHECKBOXES=$(echo "$PR_BODY" | grep -cE '\[ \]|\[x\]|\[X\]' || true)
CHECKED=$(echo "$PR_BODY" | grep -cE '\[x\]|\[X\]' || true)

echo "PR body 中有 $CHECKBOXES 个 checkboxes，已勾选 $CHECKED 个"

if [ "$CHECKBOXES" -gt 0 ] && [ "$CHECKBOXES" -eq "$CHECKED" ]; then
  echo "✅ 所有子任务 checkboxes 已勾选"
elif [ "$CHECKBOXES" -gt 0 ]; then
  UNCHECKED=$((CHECKBOXES - CHECKED))
  echo "⚠ $UNCHECKED 个子任务未完成"
fi
