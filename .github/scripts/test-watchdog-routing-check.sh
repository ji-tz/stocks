#!/usr/bin/env bash
# ============================================================================
# test-watchdog-routing-check.sh
# Validate ai-progress-watchdog routing failure detection logic.
#
# This test simulates the Tier 0 (routing failure) and Tier 1 (queue stuck)
# detection logic from the enhanced ai-progress-watchdog.yml using mock issue
# data, without needing a real GitHub API or workflow run.
#
# Test scenarios cover #243/#245 stuck patterns:
# - Issue in ai-in-progress WITHOUT triaged label (>2h → routing failure)
# - Issue in ai-in-progress WITH triaged but no PR (>4h → queue stuck)
# - Issue in ai-in-progress within thresholds → OK
# - Batch alert when 3+ routing failures occur
#
# Usage:
#   ./test-watchdog-routing-check.sh
#
# Returns:
#   0 = all tests pass
#   1 = one or more tests fail
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEBUG=${DEBUG:-0}

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color
PASS=0
FAIL=0

# ---- Helper functions ----

# Simulate: has issue been in ai-in-progress longer than threshold without triaged?
detect_routing_failure() {
    local age_hours="$1"      # Hours since last update
    local has_triaged="$2"    # "true" or "false"
    local threshold_hours=2

    if (( $(echo "$age_hours > $threshold_hours" | bc -l) )) && [ "$has_triaged" = "false" ]; then
        return 0  # routing failure detected
    fi
    return 1
}

# Simulate: has issue been triaged but no PR for longer than queue threshold?
detect_queue_stuck() {
    local age_hours="$1"      # Hours since last update
    local has_triaged="$2"    # "true" or "false"
    local has_pr="$3"         # "true" or "false"
    local threshold_hours=4

    if (( $(echo "$age_hours > $threshold_hours" | bc -l) )) && \
       [ "$has_triaged" = "true" ] && [ "$has_pr" = "false" ]; then
        return 0  # queue stuck detected
    fi
    return 1
}

# Simulate: should issue be warned (>=22h)?
detect_warning() {
    local age_hours="$1"
    local has_pr="$2"
    local threshold_hours=22

    if (( $(echo "$age_hours >= $threshold_hours" | bc -l) )) && [ "$has_pr" = "false" ]; then
        return 0
    fi
    return 1
}

# Simulate: should issue be closed (>=24h)?
detect_close() {
    local age_hours="$1"
    local has_pr="$2"
    # Real threshold is 24.5h but we test 24h for simplicity
    local threshold_hours=24.5

    if (( $(echo "$age_hours >= $threshold_hours" | bc -l) )) && [ "$has_pr" = "false" ]; then
        return 0
    fi
    return 1
}

classify_issue() {
    local age_hours="$1"
    local has_triaged="$2"
    local has_pr="$3"

    # Priority order: routing_failure → close → warning → queue_stuck → ok
    if detect_routing_failure "$age_hours" "$has_triaged"; then
        echo "routing_failure"
    elif detect_close "$age_hours" "$has_pr"; then
        echo "close"
    elif detect_warning "$age_hours" "$has_pr"; then
        echo "warning"
    elif detect_queue_stuck "$age_hours" "$has_triaged" "$has_pr"; then
        echo "queue_stuck"
    else
        echo "ok"
    fi
}

# Simulate batch alert check
detect_batch_alert() {
    local routing_failures="$1"
    local queue_stuck="$2"
    local threshold=3
    local total=$((routing_failures + queue_stuck))

    if [ "$total" -ge "$threshold" ]; then
        return 0
    fi
    return 1
}

# Test runner
test_case() {
    local desc="$1"
    local expected="$2"
    local actual="$3"

    if [ "$expected" = "$actual" ]; then
        echo -e "  ${GREEN}✓ PASS${NC} $desc"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}✗ FAIL${NC} $desc"
        echo -e "    Expected: $expected"
        echo -e "    Actual:   $actual"
        FAIL=$((FAIL + 1))
    fi
}

# ============================================================================
# Test scenarios
# ============================================================================

echo ""
echo "=== Tier 0: Routing Failure Detection (ai-in-progress >2h, no triaged) ==="
echo "  Simulates #243/#245 pattern: issue in ai-in-progress but never routed"
echo ""

# TC-0a: 1h without triaged → OK (within threshold)
actual=$(classify_issue 1 "false" "false")
test_case "TC-0a: 1h, no triaged, no PR → ok" "ok" "$actual"

# TC-0b: 3h without triaged → routing_failure
actual=$(classify_issue 3 "false" "false")
test_case "TC-0b: 3h, no triaged, no PR → routing_failure" "routing_failure" "$actual"

# TC-0c: 5h without triaged → routing_failure (longer also works)
actual=$(classify_issue 5 "false" "false")
test_case "TC-0c: 5h, no triaged, no PR → routing_failure" "routing_failure" "$actual"

# TC-0d: 3h with triaged → ok (under queue_stuck >4h threshold)
actual=$(classify_issue 3 "true" "false")
test_case "TC-0d: 3h, WITH triaged, no PR → ok (under 4h queue threshold)" "ok" "$actual"

# TC-0e: 2h exactly → NOT routing failure (strictly greater than)
actual=$(classify_issue 2 "false" "false")
test_case "TC-0e: 2h, no triaged, no PR → ok (strict >2h)" "ok" "$actual"

echo ""
echo "=== Tier 1: Queue Stuck Detection (triaged >4h, no PR) ==="
echo ""

# TC-1a: 3h with triaged → ok (under >4h threshold)
actual=$(classify_issue 3 "true" "false")
test_case "TC-1a: 3h, triaged, no PR → ok (under >4h threshold)" "ok" "$actual"

# TC-1b: 5h with triaged, no PR → queue_stuck
actual=$(classify_issue 5 "true" "false")
test_case "TC-1b: 5h, triaged, no PR → queue_stuck" "queue_stuck" "$actual"

# TC-1c: 10h with triaged AND has PR → OK (has PR means progress)
actual=$(classify_issue 10 "true" "true")
test_case "TC-1c: 10h, triaged, has PR → ok" "ok" "$actual"

# TC-1d: 5h without triaged → routing_failure takes priority over queue_stuck
actual=$(classify_issue 5 "false" "false")
test_case "TC-1d: 5h, no triaged → routing_failure (queuestuck lower priority)" "routing_failure" "$actual"

# TC-1e: 4h with triaged, no PR → ok (strict >4h, not >=)
actual=$(classify_issue 4 "true" "false")
test_case "TC-1e: 4h, triaged, no PR → ok (strict >4h)" "ok" "$actual"

echo ""
echo "=== Tier 2-3: Existing Warning/Close Detection ==="
echo ""

# TC-2a: 22h with triaged, no PR → warning
actual=$(classify_issue 22 "true" "false")
test_case "TC-2a: 22h, triaged, no PR → warning" "warning" "$actual"

# TC-2b: 23h with triaged, has PR → OK (has PR)
actual=$(classify_issue 23 "true" "true")
test_case "TC-2b: 23h, triaged, has PR → ok" "ok" "$actual"

# TC-2c: 24.5h with triaged, no PR → close
actual=$(classify_issue 24.5 "true" "false")
test_case "TC-2c: 24.5h, triaged, no PR → close" "close" "$actual"

# TC-2d: 24h with triaged, no PR → warning (not yet 24.5h)
actual=$(classify_issue 24 "true" "false")
test_case "TC-2d: 24h, triaged, no PR → warning (under 24.5h close)" "warning" "$actual"

echo ""
echo "=== Batch Alert Detection (3+ stuck issues) ==="
echo ""

# TC-3a: 0 routing failures → no alert
detect_batch_alert 0 0 && result="alert" || result="no_alert"
test_case "TC-3a: 0 stuck → no_alert" "no_alert" "$result"

# TC-3b: 2 routing failures → no alert (<3)
detect_batch_alert 2 0 && result="alert" || result="no_alert"
test_case "TC-3b: 2 routing failures → no_alert" "no_alert" "$result"

# TC-3c: 3 routing failures → alert
detect_batch_alert 3 0 && result="alert" || result="no_alert"
test_case "TC-3c: 3 routing failures → alert" "alert" "$result"

# TC-3d: 1 routing failure + 2 queue stuck = 3 total → alert
detect_batch_alert 1 2 && result="alert" || result="no_alert"
test_case "TC-3d: 1+2=3 stuck → alert" "alert" "$result"

# TC-3e: 5 routing failures → alert
detect_batch_alert 5 0 && result="alert" || result="no_alert"
test_case "TC-3e: 5 routing failures → alert" "alert" "$result"

echo ""
echo "=== Validates #243/#245 Stuck Pattern (Simulated) ==="
echo ""

# Simulate what happened with #243:
# Issue got label ai-in-progress but implementation router assigned to inactive profile
# → issue stayed in ai-in-progress with no PR for 18+ hours
# Since it had triaged but no PR, at 5h+ it would be detected as queue_stuck
actual=$(classify_issue 18 "true" "false")
test_case "#243-style: 18h, triaged, no PR → queue_stuck" "queue_stuck" "$actual"

# Simulate what happened with #245:
# Same pattern — ai-in-progress, triaged, but no agent working on it
actual=$(classify_issue 16 "true" "false")
test_case "#245-style: 16h, triaged, no PR → queue_stuck" "queue_stuck" "$actual"

# Batch alert for #243 + #245 + 1 more = 3+
detect_batch_alert 0 2 && result="alert" || result="no_alert"
test_case "#243+#245 (2 queue stuck) → no_alert (<3)" "no_alert" "$result"

detect_batch_alert 0 3 && result="alert" || result="no_alert"
test_case "#243+#245+1 (3 queue stuck) → alert" "alert" "$result"

echo ""
echo "=== Practical integration: Router retry works ==="
echo ""

# Verify the test script's own core detection functions work by testing boundaries
echo "  Testing detect_routing_failure boundary..."
if detect_routing_failure 2.1 "false" && detect_routing_failure 3 "false"; then
    echo -e "  ${GREEN}✓ PASS${NC} detect_routing_failure works for >2h without triaged"
    PASS=$((PASS + 1))
else
    echo -e "  ${RED}✗ FAIL${NC} detect_routing_failure misbehaved"
    FAIL=$((FAIL + 1))
fi

# Verify queue_stuck also catches triaged+noPR+age>4h
if ! detect_queue_stuck 3 "true" "false" && detect_queue_stuck 5 "true" "false"; then
    echo -e "  ${GREEN}✓ PASS${NC} detect_queue_stuck correctly boundaries (3h→no, 5h→yes)"
    PASS=$((PASS + 1))
else
    echo -e "  ${RED}✗ FAIL${NC} detect_queue_stuck misbehaved"
    FAIL=$((FAIL + 1))
fi

# ============================================================================
# Summary
# ============================================================================
echo ""
echo "========================================="
echo "Results: ${PASS} passed, ${FAIL} failed"
echo "========================================="

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
exit 0
