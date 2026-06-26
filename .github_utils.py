"""GitHub API utilities using ghapi."""
from ghapi.all import GhApi
import os
import sys
import json

token = open('/tmp/ghtoken.txt', encoding='utf-8').read().strip()
owner, repo = '183965983', 'stocks'

api = GhApi(owner=owner, repo=repo, token=token)

if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'comment':
        api.issues.create_comment(issue_number=int(sys.argv[2]), body=sys.argv[3])
        print(f"Posted comment on #{sys.argv[2]}")
    elif cmd == 'labels':
        api.issues.add_labels(issue_number=int(sys.argv[2]), labels=sys.argv[3:])
        print(f"Added labels to #{sys.argv[2]}")
    elif cmd == 'create_pr':
        data = json.loads(sys.argv[2])
        pr = api.pulls.create(title=data['title'], body=data['body'], head=data['head'], base=data.get('base', 'main'))
        print(f"Created PR #{pr.number}: {pr.html_url}")
    elif cmd == 'get_issue':
        issue = api.issues.get(issue_number=int(sys.argv[2]))
        print(f'#{issue.number}: {issue.title} [{issue.state}]')
