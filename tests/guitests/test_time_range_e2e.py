"""
Playwright测试：时间段设置功能的端到端测试
测试新增的时间段设置页面的真实用户交互流程
"""
import unittest
import subprocess
import sys
import time
import os
from playwright.sync_api import sync_playwright, expect


class TestTimeRangeSelectionE2E(unittest.TestCase):
    """测试时间段设置功能的端到端流程"""

    @classmethod
    def setUpClass(cls):
        """启动Flask服务器"""
        cls.server_process = subprocess.Popen(
            [sys.executable, '-m', 'gui.web'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={**os.environ, 'FLASK_ENV': 'production'}
        )
        # 等待服务器启动
        time.sleep(3)

    @classmethod
    def tearDownClass(cls):
        """关闭Flask服务器"""
        cls.server_process.terminate()
        cls.server_process.wait(timeout=5)

    def test_time_range_page_navigation(self):
        """测试导航到时间段设置页面"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                # 1. 访问首页
                page.goto('http://127.0.0.1:5000/', wait_until='networkidle')
                
                # 2. 通过API选择股票
                page.evaluate("""
                    fetch('/api/select_stock', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({code: '600900', name: '长江电力'})
                    })
                """)
                time.sleep(0.3)
                
                # 3. 导航到策略选择
                page.goto('http://127.0.0.1:5000/select_strategy', wait_until='networkidle')
                
                # 4. 通过API选择策略
                page.evaluate("""
                    fetch('/api/select_strategy', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({strategy_type: 'sma', strategy_name: 'SMA策略'})
                    })
                """)
                time.sleep(0.3)
                
                # 5. 导航到运行模式选择
                page.goto('http://127.0.0.1:5000/select_mode', wait_until='networkidle')
                
                # 6. 选择回测模式
                page.evaluate("""
                    fetch('/api/select_mode', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({mode: 'backtest'})
                    })
                """)
                time.sleep(0.3)
                
                # 7. 导航到时间段设置页面
                page.goto('http://127.0.0.1:5000/select_time_range', wait_until='networkidle')
                
                # 验证页面元素
                expect(page.locator('h1')).to_contain_text('第3.5步：设置回测时间段')
                expect(page.locator('input#start-date')).to_be_visible()
                expect(page.locator('input#end-date')).to_be_visible()
                
                # 验证已选信息显示
                expect(page.get_by_text('600900 - 长江电力')).to_be_visible()
                expect(page.get_by_text('SMA策略')).to_be_visible()
                
            finally:
                browser.close()

    def test_time_range_date_input(self):
        """测试日期输入功能"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                # 设置session
                page.goto('http://127.0.0.1:5000/', wait_until='networkidle')
                page.evaluate("""
                    async () => {
                        await fetch('/api/select_stock', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({code: '600900', name: '长江电力'})
                        });
                        await fetch('/api/select_strategy', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({strategy_type: 'sma', strategy_name: 'SMA策略'})
                        });
                        await fetch('/api/select_mode', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({mode: 'backtest'})
                        });
                    }
                """)
                time.sleep(0.5)
                
                # 导航到时间段设置页面
                page.goto('http://127.0.0.1:5000/select_time_range', wait_until='networkidle')
                
                # 填写日期
                page.fill('input#start-date', '2023-01-01')
                page.fill('input#end-date', '2023-12-31')
                
                # 验证日期已填写
                self.assertEqual(page.input_value('input#start-date'), '2023-01-01')
                self.assertEqual(page.input_value('input#end-date'), '2023-12-31')
                
                # 验证无错误提示
                error_el = page.locator('#date-error')
                self.assertFalse(error_el.is_visible())
                
            finally:
                browser.close()

    def test_time_range_preset_buttons(self):
        """测试快捷时间段按钮"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                # 设置session
                page.goto('http://127.0.0.1:5000/', wait_until='networkidle')
                page.evaluate("""
                    async () => {
                        await fetch('/api/select_stock', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({code: '600900', name: '长江电力'})
                        });
                        await fetch('/api/select_strategy', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({strategy_type: 'sma', strategy_name: 'SMA策略'})
                        });
                        await fetch('/api/select_mode', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({mode: 'backtest'})
                        });
                    }
                """)
                time.sleep(0.5)
                
                # 导航到时间段设置页面
                page.goto('http://127.0.0.1:5000/select_time_range', wait_until='networkidle')
                
                # 点击"最近1年"按钮
                page.click('button:has-text("最近1年")')
                time.sleep(0.3)
                
                # 验证日期已自动填写（开始日期应该是1年前）
                start_value = page.input_value('input#start-date')
                end_value = page.input_value('input#end-date')
                
                self.assertIsNotNone(start_value)
                self.assertIsNotNone(end_value)
                self.assertTrue(len(start_value) > 0)
                self.assertTrue(len(end_value) > 0)
                
                # 点击"清空"按钮
                page.click('button:has-text("全部数据")')
                time.sleep(0.3)
                
                # 验证日期已清空
                self.assertEqual(page.input_value('input#start-date'), '')
                self.assertEqual(page.input_value('input#end-date'), '')
                
            finally:
                browser.close()

    def test_time_range_date_validation(self):
        """测试日期验证功能"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                # 设置session
                page.goto('http://127.0.0.1:5000/', wait_until='networkidle')
                page.evaluate("""
                    async () => {
                        await fetch('/api/select_stock', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({code: '600900', name: '长江电力'})
                        });
                        await fetch('/api/select_strategy', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({strategy_type: 'sma', strategy_name: 'SMA策略'})
                        });
                        await fetch('/api/select_mode', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({mode: 'backtest'})
                        });
                    }
                """)
                time.sleep(0.5)
                
                # 导航到时间段设置页面
                page.goto('http://127.0.0.1:5000/select_time_range', wait_until='networkidle')
                
                # 填写不合法的日期（开始日期晚于结束日期）
                page.fill('input#start-date', '2023-12-31')
                page.fill('input#end-date', '2023-01-01')
                time.sleep(0.3)
                
                # 验证显示错误提示
                error_el = page.locator('#date-error')
                expect(error_el).to_be_visible()
                expect(error_el).to_contain_text('起始日期不能晚于结束日期')
                
            finally:
                browser.close()

    def test_complete_flow_with_time_range(self):
        """测试包含时间段设置的完整流程"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                # 完整流程：股票 → 策略 → 模式 → 时间段 → 策略配置
                page.goto('http://127.0.0.1:5000/', wait_until='networkidle')
                
                # 设置流程信息
                page.evaluate("""
                    async () => {
                        await fetch('/api/select_stock', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({code: '600900', name: '长江电力'})
                        });
                        await fetch('/api/select_strategy', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({strategy_type: 'sma', strategy_name: 'SMA策略'})
                        });
                        await fetch('/api/select_mode', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({mode: 'backtest'})
                        });
                    }
                """)
                time.sleep(0.5)
                
                # 导航到时间段设置并填写
                page.goto('http://127.0.0.1:5000/select_time_range', wait_until='networkidle')
                page.fill('input#start-date', '2023-01-01')
                page.fill('input#end-date', '2023-12-31')
                
                # 提交时间段
                page.evaluate("""
                    fetch('/api/select_time_range', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({start: '20230101', end: '20231231'})
                    })
                """)
                time.sleep(0.3)
                
                # 导航到策略配置页面
                page.goto('http://127.0.0.1:5000/strategy/sma', wait_until='networkidle')
                
                # 验证策略配置页面（第五步）
                expect(page.locator('h1')).to_contain_text('第五步：配置参数')
                
                # 验证没有日期输入框（已在上一步设置）
                self.assertEqual(page.locator('input[name="start"]').count(), 0)
                self.assertEqual(page.locator('input[name="end"]').count(), 0)
                
            finally:
                browser.close()


if __name__ == '__main__':
    unittest.main()
