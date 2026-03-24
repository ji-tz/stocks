const fs = require('fs');
const path = require('path');

async function commentGuitestReport({ github, context, core, artifactName = 'guitest-report' }) {
  const workspace = process.env.GITHUB_WORKSPACE || process.cwd();
  const reportPath = path.join(workspace, 'testing', 'guitest.md');
  const marker = '<!-- guitest-report -->';

  if (!fs.existsSync(reportPath)) {
    core.setFailed(`未找到报告文件: ${reportPath}`);
    return;
  }

  const reportBody = fs.readFileSync(reportPath, 'utf8').trim();
  const runUrl = `https://github.com/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId}`;
  const artifactUrl = `${runUrl}/artifacts`;
  const commentBody = [
    marker,
    reportBody,
    '',
    '---',
    `- Workflow 运行：[#${context.runId}](${runUrl})`,
    `- 测试产物： [${artifactName}](${artifactUrl})`,
  ].join('\n');

  const { data: comments } = await github.rest.issues.listComments({
    owner: context.repo.owner,
    repo: context.repo.repo,
    issue_number: context.issue.number,
    per_page: 100,
  });

  const existing = comments.find((item) => item.user?.type === 'Bot' && item.body?.includes(marker));

  if (existing) {
    await github.rest.issues.updateComment({
      owner: context.repo.owner,
      repo: context.repo.repo,
      comment_id: existing.id,
      body: commentBody,
    });
    return;
  }

  await github.rest.issues.createComment({
    owner: context.repo.owner,
    repo: context.repo.repo,
    issue_number: context.issue.number,
    body: commentBody,
  });
}

module.exports = { commentGuitestReport };