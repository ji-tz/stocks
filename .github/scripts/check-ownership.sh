#!/usr/bin/env bash
# workflow-enforcer — 检查文件所有权合规
#
# 策略（2026-09-25 起为硬约束，见 Issue #264）：
#   1. 探针/临时/残留文件 → 一律拒绝（即使落在已登记目录内）
#   2. 已登记映射的路径 → 按 AGENTS.md §四 归属（HERMES/EXCH/TRADER/STRAT/GUI/ITEST/GTEST/LEAD/…）
#   3. 中性例外（NEUTRAL，依据 AGENTS.md §4.9「第三方工具配置，无需维护」等）→ 放行
#   4. 其余未登记路径（UNKNOWN）→ **默认拒绝**，要求先在映射表或中性例外中登记
#
# 变更本脚本必须走 Issue → 分支 → PR → CI → merge 流程（脚本自身归属 HERMES）。
set -uo pipefail

BASE_REF="$1"
shift
CHANGED_FILES=("$@")

# 探针 / 临时 / 回滚残留 / 编辑器与系统垃圾 → 绝对禁止进入仓库
# 注意：不按 "probe_*" 前缀一刀切（仓库既有 probe_stocks.py 为例外登记文件），
#      以明确的 "delete-me" 标记 + 临时后缀 + 系统垃圾为准。
DENY_PATTERN='delete[-_]me|\.(tmp|bak|orig|rej|swp)$|(^|/)(\.ds_store|thumbs\.db)$|~$'

MAPPED=()
NEUTRAL=()
UNKNOWN=()
DENIED=()

# 已登记映射（对齐 AGENTS.md §4.8 / §4.9）
match_owner() {
  case "$1" in
    exchange/*)                                        echo "EXCH" ;;
    trader/*)                                          echo "TRADER" ;;
    strategy/*)                                        echo "STRAT" ;;
    gui/*)                                             echo "GUI" ;;
    tests/unit/*|tests/integration/*)                  echo "ITEST" ;;
    tests/guitests/*)                                  echo "GTEST" ;;
    tests/__init__.py|tests/README.md)                 echo "ITEST" ;;
    tests/test_comment_guitest_report_script.js)       echo "ITEST" ;;
    .github/workflows/test.yml)                        echo "ITEST" ;;
    .github/workflows/testgui.yml)                     echo "GTEST" ;;
    .github/workflows/lint.yml)                        echo "LEAD" ;;
    .github/workflows/package.yml)                     echo "TRADER" ;;
    .github/workflows/opencode.yml)                    echo "HERMES" ;;
    .github/workflows/auto-create-pr.yml)              echo "HERMES" ;;
    .github/workflows/workflow-enforcer.yml)           echo "HERMES" ;;
    .github/workflows/issue-auto-routing.yml)          echo "ARCH" ;;
    .github/workflows/ai-progress-watchdog.yml)        echo "AUDITOR" ;;
    .github/workflows/pr-merge-cleanup.yml)            echo "AUDITOR" ;;
    .github/workflows/issue-label-sync.yml)            echo "AUDITOR" ;;
    .github/workflows/README.md)                       echo "HERMES" ;;
    .github/workflows/pr-auto-assign.yml.example)      echo "AUDITOR" ;;
    .github/scripts/*)                                 echo "HERMES" ;;
    AGENTS.md)                                         echo "HERMES" ;;
    REASONIX.md)                                       echo "HERMES" ;;
    CLAUDE.md)                                         echo "ARCH" ;;
    main.py)                                           echo "GUI" ;;
    requirements.txt|pip.conf)                         echo "TRADER" ;;
    .flake8|.pylintrc|mypy.ini)                        echo "LEAD" ;;
    data/*)                                            echo "EXCH" ;;
    tools/*)                                           echo "TRADER" ;;
    README.md)                                         echo "PM" ;;
    *)                                                 echo "" ;;
  esac
}

# 中性例外：无需指定 Owner 的文档 / 第三方配置 / 调试遗留（AGENTS.md §4.9）
match_neutral() {
  case "$1" in
    docs/*)                                            echo "NEUTRAL" ;;
    .github/agents/*|.github/instructions/*|.github/skills/*) echo "NEUTRAL" ;;
    .github/copilot-instructions.md)                   echo "NEUTRAL" ;;
    .vscode/*)                                         echo "NEUTRAL" ;;
    LICENSE|.gitignore|.coverage)                      echo "NEUTRAL" ;;
    _gh.py|.github_utils.py|probe_stocks.py)           echo "NEUTRAL" ;;
    test_stocks_get_data.py)                           echo "NEUTRAL" ;;
    *)                                                 echo "" ;;
  esac
}

echo "========== 文件所有权检查（base=$BASE_REF）=========="

for file in "${CHANGED_FILES[@]}"; do
  [ -z "$file" ] && continue

  if echo "$file" | grep -qiE "$DENY_PATTERN"; then
    echo "  $file → 🚫 DENIED（探针/临时/残留文件）"
    DENIED+=("$file")
    continue
  fi

  OWNER="$(match_owner "$file")"
  if [ -z "$OWNER" ]; then
    OWNER="$(match_neutral "$file")"
    if [ -n "$OWNER" ]; then
      echo "  $file → NEUTRAL（中性例外，无 Owner 要求）"
      NEUTRAL+=("$file")
      continue
    fi
    echo "  $file → ❓ UNKNOWN（未登记）"
    UNKNOWN+=("$file")
    continue
  fi

  echo "  $file → $OWNER"
  MAPPED+=("$file")
done

echo "---------- 汇总 ----------"
echo "已登记映射: ${#MAPPED[@]}  中性例外: ${#NEUTRAL[@]}  未登记: ${#UNKNOWN[@]}  拒绝: ${#DENIED[@]}"

STATUS=0

if [ "${#DENIED[@]}" -gt 0 ]; then
  echo ""
  echo "❌ 探针/临时/残留文件禁止进入仓库："
  for f in "${DENIED[@]}"; do echo "   - $f"; done
  echo "   请删除这些文件（探针 PR 用完即删），不要提交到任何分支。"
  STATUS=1
fi

if [ "${#UNKNOWN[@]}" -gt 0 ]; then
  echo ""
  echo "❌ 未登记所有权的路径（默认拒绝）："
  for f in "${UNKNOWN[@]}"; do echo "   - $f"; done
  echo "   请先在 .github/scripts/check-ownership.sh 的映射表（或中性例外表）中登记该路径，"
  echo "   或在 AGENTS.md §四 中明确它的 Owner 后再提交。"
  STATUS=1
fi

if [ "$STATUS" -ne 0 ]; then
  echo ""
  echo "❌ 文件所有权检查未通过"
  exit 1
fi

echo "✅ 文件所有权检查完成（全部路径均已登记，无探针/临时文件）"
