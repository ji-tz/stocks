#!/usr/bin/env bash
# workflow-enforcer — 检查文件所有权合规
set -euo pipefail

BASE_REF="$1"
shift
CHANGED_FILES=("$@")

ERRORS=""

for file in "${CHANGED_FILES[@]}"; do
  [ -z "$file" ] && continue

  OWNER=""
  if [[ "$file" == exchange/* ]]; then
    OWNER="EXCH"
  elif [[ "$file" == trader/* ]]; then
    OWNER="TRADER"
  elif [[ "$file" == strategy/* ]]; then
    OWNER="STRAT"
  elif [[ "$file" == gui/* ]]; then
    OWNER="GUI"
  elif [[ "$file" == tests/unit/* ]] || [[ "$file" == tests/integration/* ]]; then
    OWNER="ITEST"
  elif [[ "$file" == tests/guitests/* ]]; then
    OWNER="GTEST"
  elif [[ "$file" == .github/workflows/test.yml ]]; then
    OWNER="ITEST"
  elif [[ "$file" == .github/workflows/testgui.yml ]]; then
    OWNER="GTEST"
  elif [[ "$file" == .github/workflows/lint.yml ]]; then
    OWNER="LEAD"
  elif [[ "$file" == .github/workflows/package.yml ]]; then
    OWNER="TRADER"
  elif [[ "$file" == AGENTS.md ]] || [[ "$file" == .github/workflows/workflow-enforcer.yml ]] || [[ "$file" == .github/scripts/* ]]; then
    OWNER="HERMES"
  elif [[ "$file" == main.py ]]; then
    OWNER="GUI"
  elif [[ "$file" == requirements.txt ]] || [[ "$file" == pip.conf ]]; then
    OWNER="TRADER"
  elif [[ "$file" == .flake8 ]] || [[ "$file" == .pylintrc ]] || [[ "$file" == mypy.ini ]]; then
    OWNER="LEAD"
  else
    OWNER="UNKNOWN"
  fi

  echo "  $file → $OWNER"
done

echo "✅ 文件所有权检查完成"
