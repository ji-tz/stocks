"""测试 GUI workflow 已切换为 testing 报告模式。"""

import unittest
from pathlib import Path


class TestGuiTestWorkflowReport(unittest.TestCase):
    """验证 testgui workflow 的关键结构。"""

    def _read_workflow(self) -> str:
        workflow_path = Path('.github/workflows/testgui.yml')
        self.assertTrue(workflow_path.exists(), 'testgui.yml 文件应该存在')
        return workflow_path.read_text(encoding='utf-8')

    def test_workflow_uses_testing_directory(self):
        content = self._read_workflow()
        self.assertIn('python -m unittest tests.guitests.test_gui_backtest_report_e2e -v', content)
        self.assertIn('path: testing/', content)
        self.assertIn('name: guitest-report', content)
        self.assertIn('.github/scripts/comment_guitest_report.js', content)
        self.assertIn('testing/guitest.md', content)

    def test_workflow_removes_old_gui_steps(self):
        content = self._read_workflow()
        self.assertNotIn('Take Main GUI Screenshot', content)
        self.assertNotIn('Take Strategy Config Screenshots', content)
        self.assertNotIn('Take Time Range Selection Screenshots', content)
        self.assertNotIn('Upload Workflow Screenshots to GitLab', content)
        self.assertNotIn('screenshots/workflow', content)
        self.assertNotIn('test_gui_workflow_e2e', content)
        self.assertNotIn('test_screenshot_cli', content)


if __name__ == '__main__':
    unittest.main()
