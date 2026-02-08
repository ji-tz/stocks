#!/usr/bin/env python3
"""
GUI 真实交互测试
使用 Playwright 进行真实的浏览器点击和操作
"""
import unittest
import os
import sys
import time
import subprocess
from unittest.mock import patch

from playwright.sync_api import sync_playwright, expect
import pandas as pd

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT_DIR)

DEFAULT_PORT = 5000


class TestGuiRoutes(unittest.TestCase):
    """GUI 真实交互测试类"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化：启动 Flask 服务器"""
        print("\n🚀 启动 Flask 服务器...")
        cls.flask_process = subprocess.Popen(
            [sys.executable, "-m", "gui.web"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=ROOT_DIR,
        )
        
        # 等待服务器启动
        print("⏳ 等待服务器就绪...")
        import requests
        max_retries = 15
        for i in range(max_retries):
            try:
                response = requests.get(f"http://127.0.0.1:{DEFAULT_PORT}/", timeout=2)
                if response.status_code == 200:
                    print(f"✅ 服务器已就绪 (尝试 {i + 1}/{max_retries})")
                    break
            except Exception:
                if i < max_retries - 1:
                    time.sleep(1)
                else:
                    print("⚠️ 服务器可能未完全就绪，继续尝试测试...")
        time.sleep(2)

    @classmethod
    def tearDownClass(cls):
        """测试类清理：关闭 Flask 服务器"""
        print("\n🛑 关闭 Flask 服务器...")
        try:
            cls.flask_process.terminate()
            cls.flask_process.wait(timeout=5)
        except Exception as e:
            print(f"⚠️ 关闭服务器时出错: {e}")
            try:
                cls.flask_process.kill()
            except Exception:
                pass

    def setUp(self):
        """每个测试前初始化浏览器"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        self.context = self.browser.new_context(viewport={"width": 1280, "height": 800})
        self.page = self.context.new_page()
        self.base_url = f"http://127.0.0.1:{DEFAULT_PORT}"

    def tearDown(self):
        """每个测试后清理浏览器"""
        self.context.close()
        self.browser.close()
        self.playwright.stop()

    def test_index_get(self):
        """测试股票选择首页 - 真实浏览器访问"""
        print("\n🧪 测试：股票选择首页")
        
        # 访问首页
        self.page.goto(self.base_url, wait_until="networkidle", timeout=30000)
        
        # 验证页面标题和关键元素
        page_content = self.page.content()
        self.assertIn('量化回测平台', page_content)
        self.assertIn('第一步：选择股票', page_content)
        self.assertIn('搜索股票', page_content)
        self.assertIn('热门股票', page_content)
        
        # 验证热门股票卡片
        self.assertIn('600900', page_content)
        self.assertIn('长江电力', page_content)
        self.assertIn('600519', page_content)
        self.assertIn('贵州茅台', page_content)
        
        print("✅ 首页元素验证通过")

    @patch('stocks.get_data')
    @patch('stocks.run_mean_cost')
    def test_run_mean_cost_post(self, mock_mean, mock_get):
        """测试均值成本策略完整流程 - 真实点击操作"""
        print("\n🧪 测试：均值成本策略完整流程")
        
        # Mock数据
        dates = pd.date_range(end="2023-12-31", periods=5, freq="D")
        df = pd.DataFrame({
            'date': dates, 'open': [100.0+i for i in range(5)], 'high': [101.0+i for i in range(5)],
            'low': [99.0+i for i in range(5)], 'close': [100.0+i for i in range(5)], 'volume': [1000+i*10 for i in range(5)]
        })
        mock_get.return_value = df
        mock_mean.return_value = {
            'symbol': '600900', 'start_date': '2023-01-01', 'end_date': '2023-01-10', 'init_cash': 100000.0,
            'trades': 1, 'total_value': 100000.0, 'market_value': 20000.0, 'realized_pl': 0.0, 'unrealized_pl': 0.0, 
            'history': [], 'trades_list': []
        }
        
        # 第一步：访问首页
        print("  步骤1: 访问首页")
        self.page.goto(self.base_url, wait_until="networkidle", timeout=30000)
        time.sleep(0.5)
        
        # 第二步：选择股票（使用API）
        print("  步骤2: 选择股票 (600900-长江电力)")
        self.page.evaluate(
            """
            fetch('/api/select_stock', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({code: '600900', name: '长江电力'})
            })
            """
        )
        time.sleep(0.5)
        
        # 第三步：导航到策略选择页面
        print("  步骤3: 导航到策略选择页面")
        self.page.goto(f"{self.base_url}/select_strategy", wait_until="networkidle")
        time.sleep(0.5)
        
        # 第四步：点击选择均值成本策略（点击卡片）
        print("  步骤4: 点击选择均值成本策略")
        self.page.locator(".strategy-card", has_text="均值成本策略").click()
        self.page.wait_for_load_state("networkidle")
        time.sleep(0.5)
        
        # 验证进入了运行模式选择页面
        self.assertIn("/select_mode", self.page.url)
        
        # 第五步：点击回测仿真
        print("  步骤5: 点击回测仿真")
        self.page.click("text=回测仿真")
        self.page.wait_for_load_state("networkidle")
        time.sleep(0.5)
        
        # 验证进入了策略配置页面
        self.assertIn("/strategy/mean_cost", self.page.url)
        
        # 第六步：填写表单参数
        print("  步骤6: 填写回测参数")
        self.page.fill('input[name="start"]', "20230101")
        self.page.fill('input[name="end"]', "20231231")
        self.page.fill('input[name="cash"]', "100000")
        
        # 第七步：点击提交按钮
        print("  步骤7: 提交表单")
        self.page.click('button[type="submit"]')
        self.page.wait_for_load_state("networkidle", timeout=60000)
        time.sleep(1)
        
        # 验证结果页面
        print("  步骤8: 验证结果页面")
        page_content = self.page.content()
        self.assertIn('平均成本策略回测结果', page_content)
        self.assertIn('总共动用资金', page_content)
        
        # 验证后端被调用
        mock_get.assert_called()
        print("✅ 均值成本策略完整流程测试通过")

    @patch('stocks.get_data')
    @patch('stocks.run_sma_backtest')
    def test_run_sma_post(self, mock_sma, mock_get):
        """测试SMA策略完整流程 - 真实点击操作"""
        print("\n🧪 测试：SMA策略完整流程")
        
        # Mock数据
        dates = pd.date_range(end="2023-12-31", periods=5, freq="D")
        df = pd.DataFrame({
            'date': dates, 'open': [100.0+i for i in range(5)], 'high': [101.0+i for i in range(5)],
            'low': [99.0+i for i in range(5)], 'close': [100.0+i for i in range(5)], 'volume': [1000+i*10 for i in range(5)]
        })
        mock_get.return_value = df
        mock_sma.return_value = {
            'symbol': '600900', 'start_date': '2023-01-01', 'end_date': '2023-01-10', 
            'init_cash': 100000.0, 'final_cash': 100500.0
        }
        
        # 第一步：访问首页并选择股票
        print("  步骤1: 访问首页并选择股票")
        self.page.goto(self.base_url, wait_until="networkidle", timeout=30000)
        self.page.evaluate(
            """
            fetch('/api/select_stock', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({code: '600900', name: '长江电力'})
            })
            """
        )
        time.sleep(0.5)
        
        # 第二步：导航到策略选择页面并选择SMA（点击卡片）
        print("  步骤2: 选择SMA策略")
        self.page.goto(f"{self.base_url}/select_strategy", wait_until="networkidle")
        self.page.locator(".strategy-card", has_text="SMA 策略").click()
        self.page.wait_for_load_state("networkidle")
        time.sleep(0.5)
        
        # 第三步：选择回测仿真
        print("  步骤3: 选择回测仿真")
        self.page.click("text=回测仿真")
        self.page.wait_for_load_state("networkidle")
        time.sleep(0.5)
        
        # 第四步：填写表单并提交
        print("  步骤4: 填写参数并提交")
        self.page.fill('input[name="start"]', "20230101")
        self.page.fill('input[name="end"]', "20231231")
        self.page.click('button[type="submit"]')
        self.page.wait_for_load_state("networkidle", timeout=60000)
        time.sleep(1)
        
        # 验证结果
        print("  步骤5: 验证结果页面")
        page_content = self.page.content()
        self.assertIn('回测结果', page_content)
        mock_get.assert_called()
        print("✅ SMA策略完整流程测试通过")

    def test_run_post_invalid_date_shows_error(self):
        """测试无效日期显示错误 - 真实表单提交"""
        print("\n🧪 测试：无效日期错误处理")
        
        # 第一步：选择股票
        print("  步骤1: 选择股票")
        self.page.goto(self.base_url, wait_until="networkidle", timeout=30000)
        self.page.evaluate(
            """
            fetch('/api/select_stock', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({code: '600900', name: '长江电力'})
            })
            """
        )
        time.sleep(0.5)
        
        # 第二步：选择SMA策略
        print("  步骤2: 选择SMA策略")
        self.page.goto(f"{self.base_url}/select_strategy", wait_until="networkidle")
        self.page.locator(".strategy-card", has_text="SMA 策略").click()
        self.page.wait_for_load_state("networkidle")
        
        # 第三步：选择回测仿真
        print("  步骤3: 选择回测仿真")
        self.page.click("text=回测仿真")
        self.page.wait_for_load_state("networkidle")
        time.sleep(0.5)
        
        # 第四步：填写无效日期并提交
        print("  步骤4: 填写无效日期")
        self.page.fill('input[name="start"]', "invalid-date")
        self.page.click('button[type="submit"]')
        self.page.wait_for_load_state("networkidle", timeout=60000)
        time.sleep(1)
        
        # 验证错误信息
        print("  步骤5: 验证错误信息")
        page_content = self.page.content()
        self.assertIn('发生错误', page_content)
        print("✅ 无效日期错误处理测试通过")

    def test_strategy_sma_get(self):
        """测试 SMA 策略配置页面 - 真实导航"""
        print("\n🧪 测试：SMA策略配置页面")
        
        # 完整流程：选择股票 → 选择策略 → 选择模式 → 查看配置页面
        print("  步骤1: 选择股票")
        self.page.goto(self.base_url, wait_until="networkidle", timeout=30000)
        self.page.evaluate(
            """
            fetch('/api/select_stock', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({code: '600900', name: '长江电力'})
            })
            """
        )
        time.sleep(0.5)
        
        print("  步骤2: 选择SMA策略")
        self.page.goto(f"{self.base_url}/select_strategy", wait_until="networkidle")
        self.page.locator(".strategy-card", has_text="SMA 策略").click()
        self.page.wait_for_load_state("networkidle")
        
        print("  步骤3: 选择回测仿真")
        self.page.click("text=回测仿真")
        self.page.wait_for_load_state("networkidle")
        time.sleep(0.5)
        
        # 验证配置页面内容
        print("  步骤4: 验证配置页面")
        page_content = self.page.content()
        self.assertIn('第四步：配置参数', page_content)
        self.assertIn('策略说明', page_content)
        self.assertIn('SMA 周期', page_content)
        self.assertIn('股票', page_content)
        self.assertIn('600900', page_content)
        self.assertIn('长江电力', page_content)
        self.assertIn('function validateDates', page_content)
    def test_strategy_mean_cost_get(self):
        """测试均值成本策略配置页面 - 真实导航"""
        print("\n🧪 测试：均值成本策略配置页面")
        
        # 完整流程：选择股票 → 选择策略 → 选择模式 → 查看配置页面
        print("  步骤1: 选择股票")
        self.page.goto(self.base_url, wait_until="networkidle", timeout=30000)
        self.page.evaluate(
            """
            fetch('/api/select_stock', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({code: '600900', name: '长江电力'})
            })
            """
        )
        time.sleep(0.5)
        
        print("  步骤2: 选择均值成本策略")
        self.page.goto(f"{self.base_url}/select_strategy", wait_until="networkidle")
        self.page.locator(".strategy-card", has_text="均值成本策略").click()
        self.page.wait_for_load_state("networkidle")
        
        print("  步骤3: 选择回测仿真")
        self.page.click("text=回测仿真")
        self.page.wait_for_load_state("networkidle")
        time.sleep(0.5)
        
        # 验证配置页面内容
        print("  步骤4: 验证配置页面")
        page_content = self.page.content()
        self.assertIn('第四步：配置参数', page_content)
        self.assertIn('策略说明', page_content)
        self.assertIn('逢低加仓', page_content)
        self.assertIn('股票', page_content)
        self.assertIn('600900', page_content)
        self.assertIn('长江电力', page_content)
        self.assertIn('function validateDates', page_content)
        print("✅ 均值成本策略配置页面测试通过")

    def test_strategy_fixed_amount_get(self):
        """测试定投策略配置页面 - 真实导航"""
        print("\n🧪 测试：定投策略配置页面")
        
        # 完整流程：选择股票 → 选择策略 → 选择模式 → 查看配置页面
        print("  步骤1: 选择股票")
        self.page.goto(self.base_url, wait_until="networkidle", timeout=30000)
        self.page.evaluate(
            """
            fetch('/api/select_stock', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({code: '600900', name: '长江电力'})
            })
            """
        )
        time.sleep(0.5)
        
        print("  步骤2: 选择定投策略")
        self.page.goto(f"{self.base_url}/select_strategy", wait_until="networkidle")
        self.page.locator(".strategy-card", has_text="定投策略").click()
        self.page.wait_for_load_state("networkidle")
        
        print("  步骤3: 选择回测仿真")
        self.page.click("text=回测仿真")
        self.page.wait_for_load_state("networkidle")
        time.sleep(0.5)
        
        # 验证配置页面内容
        print("  步骤4: 验证配置页面")
        page_content = self.page.content()
        self.assertIn('第四步：配置参数', page_content)
        self.assertIn('策略说明', page_content)
        self.assertIn('每次定投金额', page_content)
        self.assertIn('股票', page_content)
        self.assertIn('600900', page_content)
        self.assertIn('长江电力', page_content)
        self.assertIn('function validateDates', page_content)
        print("✅ 定投策略配置页面测试通过")

    @patch('stocks.get_data')
    @patch('stocks.run_mean_cost')
    def test_result_page_contains_stock_price_chart(self, mock_run, mock_get_data):
        """测试复盘界面包含股价波动线 - 真实点击操作（使用mock数据避免污染缓存）"""
        print("\n🧪 测试：复盘界面股价波动线图表")
        
        # Mock数据以避免污染data/600900.csv
        mock_df = pd.DataFrame({
            'date': pd.date_range('2023-01-01', periods=20, freq='D'),
            'open': [22.0 + i*0.1 for i in range(20)],
            'high': [22.5 + i*0.1 for i in range(20)],
            'low': [21.5 + i*0.1 for i in range(20)],
            'close': [22.0 + i*0.1 for i in range(20)],
            'volume': [1000000 + i*10000 for i in range(20)]
        })
        mock_get_data.return_value = mock_df

        # Mock回测结果 - 包含模板需要的所有字段
        mock_run.return_value = {
            'symbol': '600900',
            'start_date': '2023-01-01',
            'end_date': '2023-01-31',
            'init_cash': 100000,
            'trades': 5,
            'shares': 100,
            'cash': 95000,
            'avg_cost': 22.5,
            'total_value': 100000,
            'realized_pl': 500,
            'unrealized_pl': 200,
            'market_value': 5000,
            'max_capital_used': 50000,
            'trades_list': [
                {'date': '2023-01-01', 'action': 'buy', 'price': 22.0, 'shares': 100, 'cash': 97800, 'shares_after': 100, 'realized_pl': 0},
                {'date': '2023-01-05', 'action': 'sell', 'price': 22.5, 'shares': 50, 'cash': 98925, 'shares_after': 50, 'realized_pl': 25},
            ],
            'history': [
                {'date': '2023-01-01', 'total_value': 100000, 'last_price': 22.0},
                {'date': '2023-01-02', 'total_value': 101000, 'last_price': 22.1},
            ]
        }

        # 完整流程：选择股票 → 选择策略 → 选择模式 → 配置参数 → 提交 → 验证图表
        print("  步骤1: 选择股票")
        self.page.goto(self.base_url, wait_until="networkidle", timeout=30000)
        self.page.evaluate(
            """
            fetch('/api/select_stock', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({code: '600900', name: '长江电力'})
            })
            """
        )
        time.sleep(0.5)

        print("  步骤2: 选择均值成本策略")
        self.page.goto(f"{self.base_url}/select_strategy", wait_until="networkidle")
        self.page.locator(".strategy-card", has_text="均值成本策略").click()
        self.page.wait_for_load_state("networkidle")

        print("  步骤3: 选择回测仿真")
        self.page.click("text=回测仿真")
        self.page.wait_for_load_state("networkidle")
        time.sleep(0.5)

        print("  步骤4: 填写回测参数")
        self.page.fill('input[name="start"]', "20230101")
        self.page.fill('input[name="end"]', "20230131")
        self.page.fill('input[name="cash"]', "100000")

        print("  步骤5: 提交表单")
        self.page.click('button[type="submit"]')
        self.page.wait_for_load_state("networkidle", timeout=60000)
        time.sleep(1)

        # 验证页面包含图表元素
        print("  步骤6: 验证图表元素")
        page_content = self.page.content()
        self.assertIn('<canvas id="chart"', page_content)
        self.assertIn('totalValueData', page_content)
        self.assertIn('stockPriceData', page_content)
        self.assertIn('normalizedTotalValue', page_content)
        self.assertIn('normalizedStockPrice', page_content)
        self.assertIn("yAxisID: 'y'", page_content)
        
        print("✅ 复盘界面股价波动线图表测试通过")


if __name__ == '__main__':
    unittest.main()
