"""
Playwright测试：完整GUI工作流截图集成测试
覆盖：选择股票 -> 选择策略 -> 选择运行模式 -> 时间段 -> 配置参数 -> 回测进度 -> 结果展示
注意：历史记录功能已移除，此测试仅验证单次回测的完整流程
"""
import json
import os
import random
import subprocess
import sys
import time
import unittest
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright

ROOT_DIR = Path(__file__).resolve().parents[2]
BASE_URL = "http://127.0.0.1:5000"
SCREENSHOT_DIR = Path(
    os.environ.get(
        "GUI_WORKFLOW_SCREENSHOT_DIR",
        ROOT_DIR / "screenshots" / "workflow",
    )
)

TIME_RANGE_OPTIONS = [
    ("2023-01-01", "2023-01-31"),  # 使用较短时间范围以加快测试速度
    ("2023-06-01", "2023-06-30"),
    ("2024-01-01", "2024-01-31"),
]


def _wait_for_server_ready(timeout: float = 12.0) -> None:
    """等待Flask服务可访问"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urlopen(f"{BASE_URL}/", timeout=2) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.4)
    raise RuntimeError("Flask服务启动超时")


def _load_candidate_stocks() -> list[dict]:
    """优先选取本地有缓存数据的股票，避免依赖外部数据源"""
    data_dir = ROOT_DIR / "data"
    csv_codes = {item.stem for item in data_dir.glob("*.csv")}
    stock_list_path = ROOT_DIR / "gui" / "stock_list.json"
    candidates: list[dict] = []

    if stock_list_path.exists():
        with stock_list_path.open("r", encoding="utf-8") as handle:
            all_stocks = json.load(handle)
        candidates = [item for item in all_stocks if item.get("code") in csv_codes]

    if not candidates:
        candidates = [
            {"code": "600900", "name": "长江电力"},
            {"code": "600519", "name": "贵州茅台"},
            {"code": "000333", "name": "美的集团"},
        ]
    return candidates


class TestGuiWorkflowE2E(unittest.TestCase):
    """完整GUI工作流截图集成测试"""

    @classmethod
    def setUpClass(cls):
        """启动Flask服务器"""
        cls.server_process = subprocess.Popen(
            [sys.executable, "-m", "gui.web"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(ROOT_DIR),
            env={**os.environ, "FLASK_ENV": "production"},
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

    def _screenshot(self, page, filename: str) -> Path:
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        path = SCREENSHOT_DIR / filename
        page.screenshot(path=str(path), full_page=True)
        return path

    def test_full_gui_workflow_with_screenshots(self):
        """完整GUI工作流 + 关键节点截图（不含历史记录功能）"""
        rng = random.Random(2026)
        stock = rng.choice(_load_candidate_stocks())
        start_date, end_date = rng.choice(TIME_RANGE_OPTIONS)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 800})
            page = context.new_page()

            # 1. 打开主界面并截图
            page.goto(f"{BASE_URL}/", wait_until="networkidle")
            self._screenshot(page, "01_open_home.png")

            # 2. 选择股票进入策略选择页面并截图
            page.fill("#search-input", stock["code"])
            page.click("form#search-form button[type='submit']")
            page.wait_for_selector("#result-section.show", timeout=10000)
            page.click("button:has-text('选择此股票')")
            page.wait_for_url("**/select_strategy", timeout=10000)
            self._screenshot(page, "02_select_strategy.png")

            # 3. 选择均值成本策略，进入运行模式选择并截图
            page.click(".strategy-card:has-text('均值成本策略')")
            page.wait_for_url("**/select_mode", timeout=10000)
            self._screenshot(page, "03_select_mode.png")

            # 4. 选择回测模式，进入时间段选择并截图
            page.click(".mode-card.backtest")
            page.wait_for_url("**/select_time_range", timeout=10000)
            self._screenshot(page, "04_select_time_range.png")

            # 5. 选择时间段，进入策略配置并截图
            page.fill("#start-date", start_date)
            page.fill("#end-date", end_date)
            page.click("form#timeRangeForm button[type='submit']")
            page.wait_for_url("**/strategy/mean_cost", timeout=10000)
            self._screenshot(page, "05_mean_cost_strategy.png")

            # 6. 配置策略参数并截图
            page.select_option("select[name='source']", "auto")
            page.fill("input[name='lot']", "100")
            page.fill("input[name='cash']", "100000")
            self._screenshot(page, "06_strategy_params.png")

            # 7. 提交表单以开始回测，期望跳转到进度页面
            # 传统的 click 有时会被页面行为或覆盖层吞掉，因此
            # 这里直接使用 JavaScript 提交表单并等待导航。
            page.evaluate("() => document.querySelector('form').submit()")
            # 等待新页面的 h1 出现，它应该是“回测仿真进行中”
            page.wait_for_selector("h1", timeout=30000)
            h1_text = page.locator("h1").first.inner_text()
            if "回测仿真进行中" not in h1_text:
                page_content = page.content()
                print(f"Page after submit (first 500 chars): {page_content[:500]}")
                self._screenshot(page, "07_debug_after_submit.png")
                print(f"ERROR: Expected '回测仿真进行中' but h1 was '{h1_text}'")
                self._screenshot(page, "07_error.png")
                raise Exception(f"Expected '回测仿真进行中' but h1 was '{h1_text}'")
            self._screenshot(page, "07_backtest_progress.png")

            # 8. 等待回测完成并进入结果展示，截图
            # 注意：较短的时间范围（1个月）通常在30秒内完成，保留60秒作为缓冲
            page.wait_for_function(
                """
                () => {
                    const btn = document.getElementById('view-result-btn');
                    return btn && !btn.classList.contains('hidden');
                }
                """,
                timeout=60000,  # 使用较短时间范围后，60秒应该足够
            )
            page.click("#view-result-btn")
            page.wait_for_load_state("load", timeout=20000)
            page.wait_for_selector("canvas#chart", timeout=30000)
            self._screenshot(page, "08_backtest_result.png")

            # 验证结果页面显示正常（资产曲线图表）
            expect(page.locator("canvas#chart")).to_be_visible()

            browser.close()


if __name__ == "__main__":
    unittest.main()
