"""
GTEST: Playwright E2E tests for Issue #202 - real-time chart with buy/sell markers
during tick-by-tick backtest.

This test validates the tick-by-tick real-time chart feature on the backtest
progress page (backtest_progress.html):

  1. Canvas rendering — tickChart canvas exists and content changes as ticks arrive
  2. Buy/sell markers  — after injecting tick data with signals, green/red
     triangular markers are visible on the canvas
  3. Indicator overlays — SMA, Bollinger, volume, RSI, MACD panels appear when
     corresponding indicator data arrives
  4. No-navigation     — after the backtest completes, the current URL stays on
     the progress page
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright
from tests.guitests import _ensure_playwright_chromium

ROOT_DIR = Path(__file__).resolve().parents[2]


def _allocate_local_port() -> int:
    """Allocate a free local port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_server_ready(base_url: str, timeout: float = 30.0) -> None:
    """Wait until the Flask server responds to GET /."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urlopen(f"{base_url}/", timeout=2) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.4)
    raise RuntimeError("Flask 服务启动超时")


def _start_server_with_retry(max_attempts: int = 3) -> tuple[subprocess.Popen, str]:
    """Start the Flask server on a random port, retrying on failure."""
    last_error: Exception | None = None
    for _ in range(max_attempts):
        port = _allocate_local_port()
        base_url = f"http://127.0.0.1:{port}"
        process = subprocess.Popen(
            [sys.executable, "-m", "gui.web"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(ROOT_DIR),
            env={**os.environ, "FLASK_ENV": "production", "PORT": str(port)},
        )
        try:
            _wait_for_server_ready(base_url, timeout=30.0)
            return process, base_url
        except Exception as exc:
            last_error = exc
            process.terminate()
            try:
                process.wait(timeout=5)
            except Exception:
                process.kill()
    raise RuntimeError(f"Flask 服务重试启动失败: {last_error}")


def _count_green_red_pixels(
    page, canvas_id: str = "tickChart",
) -> dict[str, int]:
    """Count green (buy marker) and red (sell marker) pixels on the given canvas.

    Green:  g > 180, r < 100, b < 100
    Red:    r > 180, g < 100, b < 100
    """
    return page.evaluate(
        """(canvasId) => {
            const canvas = document.getElementById(canvasId);
            if (!canvas) return { greenPixels: -1, redPixels: -1, totalPixels: 0 };
            const ctx = canvas.getContext('2d');
            const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
            let greenPixels = 0, redPixels = 0;
            for (let i = 0; i < imageData.data.length; i += 4) {
                const r = imageData.data[i];
                const g = imageData.data[i + 1];
                const b = imageData.data[i + 2];
                if (g > 180 && r < 100 && b < 100) greenPixels++;
                if (r > 180 && g < 100 && b < 100) redPixels++;
            }
            return {
                greenPixels,
                redPixels,
                totalPixels: imageData.data.length / 4,
            };
        }""",
        canvas_id,
    )


class TestGuiTickByTick(unittest.TestCase):
    """Playwright E2E tests for the tick-by-tick real-time chart."""

    @classmethod
    def setUpClass(cls) -> None:
        _ensure_playwright_chromium()
        cls.server_process, cls.base_url = _start_server_with_retry()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server_process.terminate()
        try:
            cls.server_process.wait(timeout=5)
        except Exception:
            cls.server_process.kill()

    # ------------------------------------------------------------------
    # Navigation helpers
    # ------------------------------------------------------------------

    def _go_to_progress_page_with_tick(self, page) -> str:
        """Navigate the full user flow and submit an SMA backtest with
        tick_by_tick=1, returning the current progress-page URL."""
        # 1. Home → search → select stock 600900
        page.goto(f"{self.base_url}/", wait_until="networkidle")
        page.wait_for_selector("#search-input", timeout=30000)
        page.fill("#search-input", "600900")
        page.click("form#search-form button[type='submit']")
        page.wait_for_selector("#result-section.show", timeout=10000)
        page.click("button:has-text('选择此股票')")
        page.wait_for_url("**/select_strategy", timeout=10000)

        # 2. Select SMA strategy
        page.click(".strategy-card:has-text('SMA策略')")
        page.wait_for_url("**/select_mode", timeout=10000)

        # 3. Select backtest mode
        page.click(".mode-card.backtest")
        page.wait_for_url("**/select_time_range", timeout=10000)

        # 4. Set date range
        page.fill("#start-date", "2023-01-01")
        page.fill("#end-date", "2023-01-31")
        page.click("form#timeRangeForm button[type='submit']")
        page.wait_for_url("**/strategy/sma", timeout=10000)
        page.wait_for_selector(".strategy-info", timeout=30000)

        # 5. Fill SMA parameters — the SMA form has period, lot, and cash.
        #    No 'source' select exists in the base strategy_config template.
        page.fill("input[name='period']", "20")
        page.fill("input[name='lot']", "100")
        page.fill("input[name='cash']", "100000")

        # 6. Inject hidden tick_by_tick field before submitting
        page.evaluate(
            """() => {
                const form = document.querySelector('form');
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'tick_by_tick';
                input.value = '1';
                form.appendChild(input);
            }"""
        )

        # 7. Submit
        page.evaluate("() => document.querySelector('form').submit()")
        page.wait_for_selector("h1", timeout=30000)
        expect(page.locator("h1")).to_contain_text("回测仿真进行中")
        return page.url

    def _inject_ticks(self, page, ticks: list[dict]) -> None:
        """Call `addTickFull(data)` on the page for each tick data dict."""
        for tick in ticks:
            succeeded = page.evaluate(
                """(data) => {
                    if (typeof addTickFull === 'function') {
                        addTickFull(data);
                        return true;
                    }
                    return false;
                }""",
                tick,
            )
            self.assertTrue(succeeded, "addTickFull function not found on page")

    # ------------------------------------------------------------------
    # Test 1: Canvas rendering
    # ------------------------------------------------------------------

    def test_canvas_rendering(self) -> None:
        """Verify the tickChart canvas element exists and that its content
        changes as tick data arrives."""
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1440, "height": 1024}
            )
            page = context.new_page()

            progress_url = self._go_to_progress_page_with_tick(page)

            # --- Assertion A: canvas element is present and visible ---
            tick_canvas = page.locator("#tickChart")
            expect(tick_canvas).to_be_visible()

            # Chart section wrapper
            chart_section = page.locator("#chart-section")
            expect(chart_section).to_be_visible()

            # Hint starts with waiting message
            chart_hint = page.locator("#chart-hint")
            expect(chart_hint).to_contain_text("等待 tick 数据")

            # --- Assertion B: canvas content changes after tick injection ---
            # Snapshot pixel data before ticks
            before = _count_green_red_pixels(page)

            # Inject a few ticks
            self._inject_ticks(
                page,
                [
                    {
                        "date": "2023-01-03",
                        "close_price": 100.0,
                        "signal": None,
                        "indicators": {"sma": 99.5},
                    },
                    {
                        "date": "2023-01-04",
                        "close_price": 101.0,
                        "signal": None,
                        "indicators": {"sma": 100.0},
                    },
                    {
                        "date": "2023-01-05",
                        "close_price": 102.0,
                        "signal": "buy",
                        "indicators": {"sma": 100.5},
                    },
                ],
            )

            # Tick counter and price display updated
            expect(page.locator("#tick-count")).to_contain_text("Tick: 3")
            expect(page.locator("#current-price-display")).to_contain_text(
                "最新价: 102"
            )

            # Chart hint no longer shows the "waiting" message
            expect(chart_hint).to_not_contain_text("等待 tick 数据")

            # Pixel count changed (canvas was drawn onto)
            after = _count_green_red_pixels(page)
            self.assertGreater(
                after["greenPixels"],
                before["greenPixels"],
                "Green (buy-marker) pixels should appear after injecting "
                "a buy signal tick",
            )

            browser.close()

    # ------------------------------------------------------------------
    # Test 2: Buy / sell markers
    # ------------------------------------------------------------------

    def test_buy_sell_markers(self) -> None:
        """Verify green upward triangles (buy) and red downward triangles
        (sell) painted by the signalMarkers Chart.js plugin."""
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1440, "height": 1024}
            )
            page = context.new_page()

            self._go_to_progress_page_with_tick(page)

            # Inject a mix of buy / sell / neutral ticks
            self._inject_ticks(
                page,
                [
                    # Tick 0: neutral
                    {
                        "date": "2023-01-03",
                        "close_price": 100.0,
                        "signal": None,
                    },
                    # Tick 1: buy signal
                    {
                        "date": "2023-01-04",
                        "close_price": 101.5,
                        "signal": "buy",
                    },
                    # Tick 2: neutral
                    {
                        "date": "2023-01-05",
                        "close_price": 102.0,
                        "signal": None,
                    },
                    # Tick 3: sell signal
                    {
                        "date": "2023-01-06",
                        "close_price": 99.0,
                        "signal": "sell",
                    },
                ],
            )

            # Check for green and red pixels on the main chart canvas
            pixel_counts = _count_green_red_pixels(page)
            self.assertGreater(
                pixel_counts["greenPixels"],
                0,
                "Expected green pixels (buy marker) on the canvas",
            )
            self.assertGreater(
                pixel_counts["redPixels"],
                0,
                "Expected red pixels (sell marker) on the canvas",
            )

            # Also verify the legend hints appear
            expect(page.locator("#chart-hint")).to_contain_text("卖出信号")

            browser.close()

    # ------------------------------------------------------------------
    # Test 3: Strategy indicator overlays
    # ------------------------------------------------------------------

    def test_strategy_indicator_overlays(self) -> None:
        """Verify SMA / Bollinger bands / volume / RSI / MACD sub-panels
        appear when their respective indicator data arrives."""
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1440, "height": 1024}
            )
            page = context.new_page()

            self._go_to_progress_page_with_tick(page)

            # Verify initially: legends are hidden
            for legend_sel in (
                ".legend-sma",
                ".legend-bb",
                ".legend-vol",
                ".legend-rsi",
                ".legend-macd",
            ):
                expect(page.locator(legend_sel)).to_have_css(
                    "display", "none"
                )

            # Inject a tick with ALL indicator fields
            self._inject_ticks(
                page,
                [
                    {
                        "date": "2023-01-03",
                        "close_price": 100.0,
                        "signal": None,
                        "indicators": {
                            "sma": 99.5,
                            "bb_upper": 105.0,
                            "bb_middle": 100.0,
                            "bb_lower": 95.0,
                            "volume": 1500000,
                            "rsi": 55.2,
                            "macd": 0.15,
                            "macd_signal": 0.12,
                            "macd_hist": 0.03,
                        },
                    },
                    {
                        "date": "2023-01-04",
                        "close_price": 101.0,
                        "signal": None,
                        "indicators": {
                            "sma": 100.2,
                            "bb_upper": 106.0,
                            "bb_middle": 101.0,
                            "bb_lower": 96.0,
                            "volume": 1800000,
                            "rsi": 58.7,
                            "macd": 0.18,
                            "macd_signal": 0.14,
                            "macd_hist": 0.04,
                        },
                    },
                ],
            )

            # --- Legend items become visible ---
            expect(page.locator(".legend-sma")).to_be_visible()
            expect(page.locator(".legend-bb")).to_be_visible()
            expect(page.locator(".legend-vol")).to_be_visible()
            expect(page.locator(".legend-rsi")).to_be_visible()
            expect(page.locator(".legend-macd")).to_be_visible()

            # --- Sub-panel containers expand ---
            # Volume panel should always be visible after data
            vol_container = page.locator("#volume-chart-container")
            expect(vol_container).to_be_visible()

            # RSI panel appears when RSI data arrives
            rsi_container = page.locator("#rsi-chart-container")
            expect(rsi_container).to_be_visible()

            # MACD panel appears when MACD data arrives
            macd_container = page.locator("#macd-chart-container")
            expect(macd_container).to_be_visible()

            # Verify chart instances were created (side-effect of addTickFull)
            instances = page.evaluate(
                """() => ({
                    tick: typeof tickChartInstance !== 'undefined' && tickChartInstance !== null,
                    volume: typeof volumeChartInstance !== 'undefined' && volumeChartInstance !== null,
                    rsi: typeof rsiChartInstance !== 'undefined' && rsiChartInstance !== null,
                    macd: typeof macdChartInstance !== 'undefined' && macdChartInstance !== null,
                })"""
            )
            self.assertTrue(instances["tick"], "Main tick chart not created")
            self.assertTrue(
                instances["volume"], "Volume chart instance not created"
            )
            self.assertTrue(
                instances["rsi"], "RSI chart instance not created"
            )
            self.assertTrue(
                instances["macd"], "MACD chart instance not created"
            )

            browser.close()

    # ------------------------------------------------------------------
    # Test 4: No-navigation
    # ------------------------------------------------------------------

    def test_no_navigation_after_backtest_completes(self) -> None:
        """After the backtest finishes, the user stays on the same page
        (URL unchanged, no redirect)."""
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1440, "height": 1024}
            )
            page = context.new_page()

            progress_url = self._go_to_progress_page_with_tick(page)

            # Wait for the backtest to finish — the "view result" button
            # appears as a signal of completion (the SSE completed event
            # triggers startReplay then finishReplay).
            page.wait_for_function(
                """() => {
                    const btn = document.getElementById('view-result-btn');
                    return btn && !btn.classList.contains('hidden');
                }""",
                timeout=120000,
            )

            # URL must NOT have changed — still on the progress page
            current_url = page.url
            self.assertEqual(
                current_url,
                progress_url,
                "URL changed after backtest completion — "
                f"expected {progress_url}, got {current_url}",
            )

            # Status indicator should show 'completed'
            status_completed = page.locator("#status-completed")
            expect(status_completed).to_be_visible()
            expect(status_completed).to_contain_text("回放完成")

            # Progress bar should show 100%
            expect(page.locator("#progress-percentage")).to_contain_text(
                "100%"
            )

            # The page title / h1 is still "回测仿真进行中"
            expect(page.locator("h1")).to_contain_text("回测仿真进行中")

            browser.close()


if __name__ == "__main__":
    unittest.main()
