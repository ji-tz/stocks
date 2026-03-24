"""GUI 量化回测主流程测试。

该测试会真实启动 Flask 服务，使用 Playwright 完成一次完整量化回测，
并将每一步截图与 Markdown 报告统一输出到 testing 目录。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import unittest
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright
from tests.guitests import _ensure_playwright_chromium


ROOT_DIR = Path(__file__).resolve().parents[2]
BASE_URL = "http://127.0.0.1:5001"
TESTING_DIR = ROOT_DIR / "testing"
REPORT_PATH = TESTING_DIR / "guitest.md"


def _wait_for_server_ready(timeout: float = 15.0) -> None:
    """等待 Flask 服务启动完成。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urlopen(f"{BASE_URL}/", timeout=2) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.4)
    raise RuntimeError("Flask 服务启动超时")


class TestGuiBacktestReportE2E(unittest.TestCase):
    """完整回测流程，生成 testing 目录产物。"""

    @classmethod
    def setUpClass(cls) -> None:
        _ensure_playwright_chromium()
        shutil.rmtree(TESTING_DIR, ignore_errors=True)
        TESTING_DIR.mkdir(parents=True, exist_ok=True)
        cls.server_process = subprocess.Popen(
            [sys.executable, "-m", "gui.web"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(ROOT_DIR),
            env={**os.environ, "FLASK_ENV": "production", "PORT": "5001"},
        )
        _wait_for_server_ready()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server_process.terminate()
        try:
            cls.server_process.wait(timeout=5)
        except Exception:
            cls.server_process.kill()

    def _screenshot(self, page, filename: str) -> str:
        path = TESTING_DIR / filename
        page.screenshot(path=str(path), full_page=True)
        return filename

    def _write_report(self, steps: list[tuple[str, str, str]], result_summary: list[str]) -> None:
        lines = [
            "# GUI 量化回测测试报告",
            "",
            "## 测试结论",
            "",
            "- 结果：成功完成一次浏览器端量化回测",
            "- 股票：600900 长江电力",
            "- 策略：均值成本策略",
            "- 模式：回测仿真",
            "- 时间范围：2023-01-01 至 2023-01-31",
            f"- 执行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "- 产物目录：testing",
            "",
            "## 测试步骤",
            "",
        ]

        for index, (title, description, screenshot) in enumerate(steps, start=1):
            lines.extend(
                [
                    f"### 步骤 {index}：{title}",
                    "",
                    description,
                    "",
                    f"![步骤 {index} - {title}]({screenshot})",
                    "",
                ]
            )

        lines.extend(
            [
                "## 结果摘要",
                "",
                *[f"- {item}" for item in result_summary],
                "",
                "## 验收说明",
                "",
                "- 所有截图均由 Playwright 在 Chromium 浏览器中完成并保存在 testing 目录。",
                "- 报告内容可直接作为 PR 评论正文使用。",
            ]
        )

        REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    def test_generate_gui_backtest_report(self) -> None:
        steps: list[tuple[str, str, str]] = []

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 1024})
            page = context.new_page()

            page.goto(f"{BASE_URL}/", wait_until="networkidle")
            page.wait_for_selector("#search-input", timeout=30000)
            steps.append(
                (
                    "打开首页",
                    "进入量化回测首页，确认股票搜索框与热门股票区域可见。",
                    self._screenshot(page, "01_open_home.png"),
                )
            )

            page.fill("#search-input", "600900")
            page.click("form#search-form button[type='submit']")
            page.wait_for_selector("#result-section.show", timeout=10000)
            page.click("button:has-text('选择此股票')")
            page.wait_for_url("**/select_strategy", timeout=10000)
            steps.append(
                (
                    "选择股票",
                    "搜索 600900 并确认跳转到策略选择页。",
                    self._screenshot(page, "02_select_strategy.png"),
                )
            )

            page.click(".strategy-card:has-text('均值成本策略')")
            page.wait_for_url("**/select_mode", timeout=10000)
            steps.append(
                (
                    "选择策略",
                    "选择均值成本策略，进入运行模式选择页。",
                    self._screenshot(page, "03_select_mode.png"),
                )
            )

            page.click(".mode-card.backtest")
            page.wait_for_url("**/select_time_range", timeout=10000)
            steps.append(
                (
                    "选择运行模式",
                    "选择回测仿真模式，进入时间范围设置页。",
                    self._screenshot(page, "04_select_time_range.png"),
                )
            )

            page.fill("#start-date", "2023-01-01")
            page.fill("#end-date", "2023-01-31")
            page.click("form#timeRangeForm button[type='submit']")
            page.wait_for_url("**/strategy/mean_cost", timeout=10000)
            page.wait_for_selector("#realtime-info", timeout=30000)
            steps.append(
                (
                    "设置回测时间段",
                    "设置 2023-01-01 到 2023-01-31 的回测区间，并进入策略参数页。",
                    self._screenshot(page, "05_mean_cost_strategy.png"),
                )
            )

            page.select_option("select[name='source']", "auto")
            page.fill("input[name='lot']", "100")
            page.fill("input[name='cash']", "100000")
            expect(page.locator("#realtime-info")).to_be_visible()
            steps.append(
                (
                    "配置策略参数",
                    "使用自动数据源、每手 100 股、初始资金 100000 元，并确认实时计算区域正常显示。",
                    self._screenshot(page, "06_strategy_params.png"),
                )
            )

            page.evaluate("() => document.querySelector('form').submit()")
            page.wait_for_selector("h1", timeout=30000)
            expect(page.locator("h1")).to_contain_text("回测仿真进行中")
            steps.append(
                (
                    "运行回测",
                    "提交参数后进入回测进度页，确认进度展示页面正常加载。",
                    self._screenshot(page, "07_backtest_progress.png"),
                )
            )

            page.wait_for_function(
                """
                () => {
                    const btn = document.getElementById('view-result-btn');
                    return btn && !btn.classList.contains('hidden');
                }
                """,
                timeout=60000,
            )
            page.click("#view-result-btn")
            page.wait_for_load_state("load", timeout=20000)
            page.wait_for_selector("canvas#chart", timeout=30000)
            steps.append(
                (
                    "查看回测结果",
                    "回测完成后进入结果页，确认资产曲线图和结果摘要已经展示。",
                    self._screenshot(page, "08_backtest_result.png"),
                )
            )

            summary_cards = page.locator(".summary .card").all_inner_texts()
            result_summary = [item.strip() for item in summary_cards if item.strip()]
            self.assertTrue(result_summary, "结果页摘要不能为空")
            self._write_report(steps, result_summary)

            browser.close()

        expected_outputs = [
            "01_open_home.png",
            "02_select_strategy.png",
            "03_select_mode.png",
            "04_select_time_range.png",
            "05_mean_cost_strategy.png",
            "06_strategy_params.png",
            "07_backtest_progress.png",
            "08_backtest_result.png",
            "guitest.md",
        ]
        for name in expected_outputs:
            self.assertTrue((TESTING_DIR / name).exists(), f"缺少产物: {name}")


if __name__ == "__main__":
    unittest.main()