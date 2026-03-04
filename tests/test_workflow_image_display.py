#!/usr/bin/env python3
"""测试 workflow 的 PR 评论与截图汇总配置。"""

import unittest
from pathlib import Path


class TestWorkflowConfiguration(unittest.TestCase):
    """测试 GUI workflow 关键结构。"""

    def _read_testgui_content(self) -> str:
        workflow_path = Path('.github/workflows/testgui.yml')
        self.assertTrue(workflow_path.exists(), 'testgui.yml 文件应该存在')
        return workflow_path.read_text(encoding='utf-8')

    def test_testgui_workflow_exists(self):
        """测试 testgui.yml 文件存在。"""
        workflow_path = Path('.github/workflows/testgui.yml')
        self.assertTrue(workflow_path.exists(), 'testgui.yml 文件应该存在')

    def test_testgui_workflow_permissions(self):
        """测试 PR 评论所需权限已配置。"""
        content = self._read_testgui_content()
        self.assertIn('permissions:', content)
        self.assertIn('pull-requests: write', content)
        self.assertIn('issues: write', content)

    def test_testgui_workflow_comment_step_structure(self):
        """测试评论步骤支持 GitLab 图片渲染与回退方案。"""
        content = self._read_testgui_content()

        # 基本步骤存在
        self.assertIn('Comment PR with Screenshots', content)
        self.assertIn('actions/github-script@v7', content)

        # Upload artifact 步骤必须有 id，便于在评论中拼接链接
        self.assertIn('id: upload_screenshots', content)
        self.assertIn('id: upload_test_results', content)
        self.assertIn('steps.upload_screenshots.outputs.artifact-id', content)
        self.assertIn('steps.upload_test_results.outputs.artifact-id', content)

        # GitLab 上传步骤与输出
        self.assertIn('Upload Workflow Screenshots to GitLab', content)
        self.assertIn('id: upload_gitlab_images', content)
        self.assertIn('steps.upload_gitlab_images.outputs.has_gitlab_images', content)
        self.assertIn('steps.upload_gitlab_images.outputs.uploaded_count', content)
        self.assertIn('gitlab_uploaded_images.json', content)
        self.assertIn('GITLAB_PROJECT_ID', content)
        self.assertIn('GITLAB_TOKEN', content)

        # 评论应包含步骤级截图状态表与下载链接
        self.assertIn('GUI流程截图报告', content)
        self.assertIn('流程步骤 | 状态 | 文件 | 大小', content)
        self.assertIn('截图产物 gui-screenshots', content)
        self.assertIn('测试结果产物 gui-test-results', content)
        self.assertIn('步骤截图预览（GitLab Markdown 渲染）', content)
        self.assertIn('![${title}](${uploaded.url})', content)

        # Sticky comment（更新已有机器人评论）
        self.assertIn("marker = '<!-- gui-workflow-screenshots -->'", content)
        self.assertIn('issues.listComments', content)
        self.assertIn('issues.updateComment', content)
        self.assertIn('issues.createComment', content)

        # 新方案不再使用 base64 data URL 嵌图
        self.assertNotIn('imageToDataUrl', content)
        self.assertNotIn('formatImageDisplay', content)
        self.assertNotIn('data:image/png;base64', content)

    def test_workflow_step_screenshot_mapping(self):
        """测试 8 个完整流程截图文件都在评论脚本中定义。"""
        content = self._read_testgui_content()
        expected_files = [
            'screenshots/workflow/01_open_home.png',
            'screenshots/workflow/02_select_strategy.png',
            'screenshots/workflow/03_select_mode.png',
            'screenshots/workflow/04_select_time_range.png',
            'screenshots/workflow/05_mean_cost_strategy.png',
            'screenshots/workflow/06_strategy_params.png',
            'screenshots/workflow/07_backtest_progress.png',
            'screenshots/workflow/08_backtest_result.png',
        ]
        for item in expected_files:
            self.assertIn(item, content)

    def test_test_workflow_exists(self):
        """测试 test.yml 文件存在。"""
        workflow_path = Path('.github/workflows/test.yml')
        self.assertTrue(workflow_path.exists(), 'test.yml 文件应该存在')


if __name__ == '__main__':
    unittest.main()
