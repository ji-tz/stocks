const assert = require('assert');
const {
  rewriteImageLinks,
} = require('../.github/scripts/comment_guitest_report.js');

function testRewriteRelativeImageLinks() {
  const input = [
    '# 报告',
    '',
    '![步骤1](01_open_home.png)',
    '![步骤2](images/02_select_strategy.png)',
    '![外链](https://example.com/a.png)',
  ].join('\n');
  const baseUrl = 'https://raw.githubusercontent.com/183965983/stocks/guitest-assets/runs/123';

  const output = rewriteImageLinks(input, baseUrl);
  assert.ok(output.includes('![步骤1](https://raw.githubusercontent.com/183965983/stocks/guitest-assets/runs/123/01_open_home.png)'));
  assert.ok(output.includes('![步骤2](https://raw.githubusercontent.com/183965983/stocks/guitest-assets/runs/123/02_select_strategy.png)'));
  assert.ok(output.includes('![外链](https://example.com/a.png)'));
}

function testKeepOriginalWhenBaseIsEmpty() {
  const input = '![步骤1](01_open_home.png)';
  const output = rewriteImageLinks(input, '');
  assert.strictEqual(output, input);
}

function run() {
  testRewriteRelativeImageLinks();
  testKeepOriginalWhenBaseIsEmpty();
  console.log('test_comment_guitest_report_script.js OK');
}

run();