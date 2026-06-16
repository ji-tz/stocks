#!/usr/bin/env python3
"""检查 PR 评论中是否存在 QA 验收通过记录"""
import json, sys

comments_json = sys.stdin.read()
if not comments_json.strip():
    print("NOT_FOUND")
    sys.exit(0)

try:
    comments = json.loads(comments_json)
except json.JSONDecodeError:
    print("NOT_FOUND")
    sys.exit(0)

for c in comments:
    body = c.get("body", "")
    has_qa_label = ("QA" in body or "验收" in body or "gtest" in body.lower())
    has_pass_signal = ("通过" in body or "PASS" in body or "✅" in body or "完成" in body)
    if has_qa_label and has_pass_signal:
        print("FOUND")
        sys.exit(0)

print("NOT_FOUND")
