"""Playwright测试：时间段设置功能端到端测试。

本文件中的每个测试都从首页出发，按真实用户路径完成：
选择股票 -> 选择策略 -> 选择运行模式 -> 时间段设置。
"""
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright


ROOT_DIR = Path(__file__).resolve().parents[2]
BASE_URL = "http://127.0.0.1:5001"


def _wait_for_server_ready(timeout: float = 12.0) -> None:
    """等待 Flask 服务启动完成。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urlopen(f"{BASE_URL}/", timeout=2) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.3)
    raise RuntimeError("Flask 服务启动超时")


class TestTimeRangeSelectionE2E(unittest.TestCase):
    """测试时间段设置功能（完整流程进入）。"""

    @classmethod
    def setUpClass(cls):
        """启动Flask服务器"""
        cls.server_process = subprocess.Popen(
            [sys.executable, '-m', 'gui.web'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(ROOT_DIR),
            env={**os.environ, 'FLASK_ENV': 'production', 'PORT': '5001'}
        )
        _wait_for_server_ready()

    @classmethod
    def tearDownClass(cls):
        """关闭Flask服务器"""
        cls.server_process.terminate()
        try:
            cls.server_process.wait(timeout=5)
        except Exception:
            cls.server_process.kill()

    def _goto_time_range_page(self, page) -> None:
        """按真实用户流程进入时间段设置页面。"""
        page.goto(f"{BASE_URL}/", wait_until='networkidle')

        # 等待搜索输入框可用后再填充
        page.wait_for_selector('#search-input', timeout=30000)
        page.fill('#search-input', '600900')
        page.click("form#search-form button[type='submit']")
        page.wait_for_selector('#result-section.show', timeout=10000)
        page.click("button:has-text('选择此股票')")
        page.wait_for_url('**/select_strategy', timeout=10000)

        page.click(".strategy-card:has-text('SMA')")
        page.wait_for_url('**/select_mode', timeout=10000)

        page.click('.mode-card.backtest')
        page.wait_for_url('**/select_time_range', timeout=10000)

    def test_time_range_page_in_full_flow(self):
        """完整流程进入时间段页面并验证关键元素。"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            try:
                self._goto_time_range_page(page)
                expect(page.locator('h1')).to_contain_text('第3.5步：设置回测时间段')
                expect(page.locator('input#start-date')).to_be_visible()
                expect(page.locator('input#end-date')).to_be_visible()
                expect(page.get_by_text('600900 - 长江电力')).to_be_visible()
                expect(page.get_by_text('SMA')).to_be_visible()
            finally:
                browser.close()

    def test_time_range_date_input_in_full_flow(self):
        """完整流程下测试日期输入。"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            try:
                self._goto_time_range_page(page)
                page.fill('input#start-date', '2023-01-01')
                page.fill('input#end-date', '2023-12-31')
                self.assertEqual(page.input_value('input#start-date'), '2023-01-01')
                self.assertEqual(page.input_value('input#end-date'), '2023-12-31')
                error_el = page.locator('#date-error')
                self.assertFalse(error_el.is_visible())
            finally:
                browser.close()

    def test_time_range_preset_buttons_in_full_flow(self):
        """完整流程下测试快捷时间段按钮。"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            try:
                self._goto_time_range_page(page)
                page.click('button:has-text("最近1年")')
                time.sleep(0.3)
                start_value = page.input_value('input#start-date')
                end_value = page.input_value('input#end-date')
                self.assertIsNotNone(start_value)
                self.assertIsNotNone(end_value)
                self.assertTrue(len(start_value) > 0)
                self.assertTrue(len(end_value) > 0)
                page.click('button:has-text("全部数据")')
                time.sleep(0.3)
                self.assertEqual(page.input_value('input#start-date'), '')
                self.assertEqual(page.input_value('input#end-date'), '')
            finally:
                browser.close()

    def test_time_range_date_validation_in_full_flow(self):
        """完整流程下测试日期校验。"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            try:
                self._goto_time_range_page(page)
                page.fill('input#start-date', '2023-12-31')
                page.fill('input#end-date', '2023-01-01')
                time.sleep(0.3)
                error_el = page.locator('#date-error')
                expect(error_el).to_be_visible()
                expect(error_el).to_contain_text('起始日期不能晚于结束日期')
            finally:
                browser.close()

    def test_time_range_submit_to_strategy_page_in_full_flow(self):
        """完整流程下提交时间段并进入策略配置页面。"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            try:
                self._goto_time_range_page(page)
                page.fill('input#start-date', '2023-01-01')
                page.fill('input#end-date', '2023-12-31')

                page.click("form#timeRangeForm button[type='submit']")
                page.wait_for_url('**/strategy/sma', timeout=10000)
                expect(page.locator('h1')).to_contain_text('第五步：配置参数')
                self.assertEqual(page.locator('input[name="start"]').count(), 0)
                self.assertEqual(page.locator('input[name="end"]').count(), 0)
            finally:
                browser.close()


if __name__ == '__main__':
    unittest.main()
