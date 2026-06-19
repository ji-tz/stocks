#!/usr/bin/env python3
"""GitHub API helper - post comment, manage labels."""
import json
import sys
import urllib.request
import urllib.error

TOKEN_FILE = "/tmp/ghtoken.txt"

def get_token():
    with open(TOKEN_FILE) as f:
        return f.read().strip()

def api(method, path, data=None):
    token = get_token()
    url = f"https://api.github.com/repos/183965983/stocks{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Hermes-Agent",
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            result = resp.read().decode()
            return json.loads(result)
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        return {"error": True, "status": e.code, "body": err}

def post_comment(issue_num, body):
    return api("POST", f"/issues/{issue_num}/comments", {"body": body})

def update_labels(issue_num, labels):
    return api("PUT", f"/issues/{issue_num}/labels", {"labels": labels})

def get_labels(issue_num):
    return api("GET", f"/issues/{issue_num}/labels")

def remove_label(issue_num, label):
    return api("DELETE", f"/issues/{issue_num}/labels/{label}")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "comment":
        num = int(sys.argv[2])
        body = sys.argv[3]
        result = post_comment(num, body)
        if result.get("error"):
            print(f"FAIL: {result}")
        else:
            print(f"Comment #{result['id']} posted on #{num}")
    elif cmd == "set_labels":
        num = int(sys.argv[2])
        labels = sys.argv[3:]
        result = update_labels(num, labels)
        if isinstance(result, list):
            names = [l["name"] for l in result]
            print(f"Labels set on #{num}: {names}")
        else:
            print(f"FAIL: {result}")
    elif cmd == "del_label":
        num = int(sys.argv[2])
        label = sys.argv[3]
        result = remove_label(num, label)
        if result.get("error"):
            print(f"FAIL to remove {label} from #{num}: {result}")
        else:
            print(f"Removed label '{label}' from #{num}")
    else:
        print("Commands: comment <num> <body> | set_labels <num> <label...> | del_label <num> <label>")
