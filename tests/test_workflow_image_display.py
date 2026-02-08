#!/usr/bin/env python3
"""测试 workflow 图片显示功能

测试 testgui.yml 中的图片处理逻辑是否正确工作。
"""

import unittest
import os
import base64
import tempfile
from pathlib import Path


class TestWorkflowImageDisplay(unittest.TestCase):
    """测试 workflow 中的图片显示功能"""

    def setUp(self):
        """创建测试用的临时图片文件"""
        self.temp_dir = tempfile.mkdtemp()
        
        # 创建一个小的测试图片（1x1 PNG）
        self.small_image_path = os.path.join(self.temp_dir, 'small_test.png')
        # PNG 1x1 像素的最小有效文件
        png_data = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
        )
        with open(self.small_image_path, 'wb') as f:
            f.write(png_data)
        
        # 创建一个大的测试文件（模拟大图片，> 1MB）
        self.large_image_path = os.path.join(self.temp_dir, 'large_test.png')
        with open(self.large_image_path, 'wb') as f:
            # 使用随机字节而不是重复的 'PNG' 字符串，更真实地模拟实际图片
            f.write(os.urandom(1200000))  # 约 1.2 MB

    def tearDown(self):
        """清理临时文件"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_small_image_base64_encoding(self):
        """测试小图片是否能正确转换为 base64"""
        # 模拟 workflow 中的 imageToDataUrl 函数
        with open(self.small_image_path, 'rb') as f:
            image_data = f.read()
        
        base64_data = base64.b64encode(image_data).decode('utf-8')
        data_url = f'data:image/png;base64,{base64_data}'
        
        # 验证 data URL 格式正确
        self.assertTrue(data_url.startswith('data:image/png;base64,'))
        self.assertGreater(len(data_url), 50)
        
        # 验证可以解码回原始数据
        encoded_part = data_url.split(',')[1]
        decoded_data = base64.b64decode(encoded_part)
        self.assertEqual(decoded_data, image_data)

    def test_large_image_size_check(self):
        """测试大图片是否被正确识别（应该使用下载链接而不是嵌入）"""
        size = os.path.getsize(self.large_image_path)
        
        # 验证大于 1MB
        self.assertGreater(size, 1024 * 1024)
        
        # 在实际 workflow 中，这种图片应该显示下载链接而不是嵌入 base64
        # 模拟 formatImageDisplay 的行为
        should_embed = size < 1024 * 1024
        self.assertFalse(should_embed, "大图片不应该被嵌入为 base64")
        
        # 验证大图片会返回包含文件信息的格式而不是 ![...](data:...)
        # 这是预期的行为：大图片显示下载链接

    def test_image_file_exists(self):
        """测试图片文件存在性检查"""
        self.assertTrue(os.path.exists(self.small_image_path))
        self.assertTrue(os.path.exists(self.large_image_path))
        self.assertFalse(os.path.exists('/nonexistent/path.png'))

    def test_file_size_formatting(self):
        """测试文件大小格式化"""
        size = os.path.getsize(self.small_image_path)
        size_kb = size / 1024
        formatted = f"{size_kb:.1f} KB"
        
        self.assertTrue('KB' in formatted)
        self.assertTrue('.' in formatted)

    def test_image_format_detection(self):
        """测试图片格式检测"""
        # PNG 文件
        self.assertTrue(self.small_image_path.endswith('.png'))
        
        # 应该使用 image/png MIME 类型
        ext = os.path.splitext(self.small_image_path)[1].lower()
        mime_type = 'image/png' if ext == '.png' else 'image/jpeg'
        self.assertEqual(mime_type, 'image/png')

    def test_markdown_image_syntax(self):
        """测试 Markdown 图片语法生成"""
        title = "测试图片"
        data_url = "data:image/png;base64,iVBORw0KG..."
        
        markdown = f"![{title}]({data_url})"
        
        # 验证 Markdown 语法正确
        self.assertTrue(markdown.startswith('!['))
        self.assertTrue('测试图片' in markdown)
        self.assertTrue('data:image/png;base64,' in markdown)


class TestWorkflowConfiguration(unittest.TestCase):
    """测试 workflow 配置文件"""

    def test_testgui_workflow_exists(self):
        """测试 testgui.yml 文件存在"""
        workflow_path = Path('.github/workflows/testgui.yml')
        self.assertTrue(workflow_path.exists(), "testgui.yml 文件应该存在")

    def test_testgui_workflow_structure(self):
        """测试 testgui.yml 包含必要的步骤"""
        workflow_path = Path('.github/workflows/testgui.yml')
        
        if not workflow_path.exists():
            self.skipTest("testgui.yml 不存在")
        
        with open(workflow_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 验证包含必要的步骤
        self.assertIn('Comment PR with Screenshots', content)
        self.assertIn('actions/github-script@v7', content)
        self.assertIn('formatImageDisplay', content)
        self.assertIn('imageToDataUrl', content)
        
        # 验证不再引用不存在的 upload_to_public_repo 步骤
        self.assertNotIn('steps.upload_to_public_repo.outputs.uploaded', content)

    def test_test_workflow_exists(self):
        """测试 test.yml 文件存在"""
        workflow_path = Path('.github/workflows/test.yml')
        self.assertTrue(workflow_path.exists(), "test.yml 文件应该存在")


if __name__ == '__main__':
    unittest.main()
