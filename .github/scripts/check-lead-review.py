#!/usr/bin/env python3
"""检查 PR 评论中是否存在 LEAD Review"""
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
    if "LEAD" in body or "审查" in body:
        # 找关键词: LEAD Review / LEAD审查 / 研发主管
        print("FOUND")
        sys.exit(0)

print("NOT_FOUND")
