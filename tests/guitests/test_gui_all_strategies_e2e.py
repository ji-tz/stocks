from __future__ import annotations

import shutil
import unittest
from pathlib import Path

import pandas as pd

import trader.stocks as stocks
from playwright.sync_api import expect, sync_playwright
from tests.guitests import _ensure_playwright_chromium
from tests.guitests.test_gui_backtest_report_e2e import ROOT_DIR, _start_server_with_retry


DATA_DIR = ROOT_DIR / 'data'


def _ensure_a50_cache() -> None:
    cache_file = DATA_DIR / 'CN00Y.csv'
    if cache_file.exists():
        return

    try:
        df = stocks.get_data(symbol='CN00Y', source='akshare', cache_dir=str(DATA_DIR))
        if df is not None and not df.empty:
            return
    except Exception:
        pass

    # 回退：用已有缓存股票生成一份可用的 A50 仿真数据，保证 GUI 测试稳定。
    stock_cache = DATA_DIR / '600900.csv'
    if not stock_cache.exists():
        raise RuntimeError('缺少 600900.csv，无法为 A50 GUI 测试生成回退缓存')

    df = pd.read_csv(stock_cache)
    for column in ('open', 'high', 'low', 'close'):
        df[column] = pd.to_numeric(df[column], errors='coerce') * 0.95
    df.to_csv(cache_file, index=False)


class TestGuiAllStrategiesE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _ensure_playwright_chromium()
        _ensure_a50_cache()
        cls.server_process, cls.base_url = _start_server_with_retry()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server_process.terminate()
        try:
            cls.server_process.wait(timeout=5)
        except Exception:
            cls.server_process.kill()

    def _goto_strategy_form(self, page, strategy_text: str, strategy_url: str) -> None:
        page.goto(f"{self.base_url}/", wait_until='networkidle')
        page.fill('#search-input', '600900')
        page.click("form#search-form button[type='submit']")
        page.wait_for_selector('#result-section.show', timeout=10000)
        page.click("button:has-text('选择此股票')")
        page.wait_for_url('**/select_strategy', timeout=10000)
        page.click(f".strategy-card:has-text('{strategy_text}')")
        page.wait_for_url('**/select_mode', timeout=10000)
        page.click('.mode-card.backtest')
        page.wait_for_url('**/select_time_range', timeout=10000)
        page.fill('#start-date', '2023-01-01')
        page.fill('#end-date', '2023-01-31')
        page.click("form#timeRangeForm button[type='submit']")
        page.wait_for_url(strategy_url, timeout=10000)

    def _submit_and_wait_result(self, page) -> None:
        page.evaluate("() => document.querySelector('form').submit()")
        page.wait_for_selector('h1', timeout=30000)
        expect(page.locator('h1')).to_contain_text('回测仿真进行中')
        expect(page.locator('#skip-btn')).to_be_visible()
        page.click('#skip-btn')
        page.wait_for_function(
            """
            () => {
                const btn = document.getElementById('view-result-btn');
                return btn && !btn.classList.contains('hidden');
            }
            """,
            timeout=120000,
        )
        page.click('#view-result-btn')
        page.wait_for_load_state('load', timeout=20000)
        page.wait_for_selector('canvas#chart', timeout=30000)
        expect(page.locator('.summary')).to_be_visible()

    def _run_strategy_flow(self, strategy_text: str, strategy_url: str, filler) -> None:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={'width': 1440, 'height': 1024})
            page = context.new_page()
            self._goto_strategy_form(page, strategy_text, strategy_url)
            filler(page)
            self._submit_and_wait_result(page)
            browser.close()

    def test_sma_strategy_gui_backtest_flow(self) -> None:
        def filler(page):
            page.fill("input[name='period']", '20')
            page.select_option("select[name='source']", 'auto')
            page.fill("input[name='lot']", '100')
            page.fill("input[name='cash']", '100000')

        self._run_strategy_flow('SMA策略', '**/strategy/sma', filler)

    def test_mean_cost_strategy_gui_backtest_flow(self) -> None:
        def filler(page):
            page.select_option("select[name='source']", 'auto')
            page.fill("input[name='lot']", '100')
            page.fill("input[name='cash']", '100000')

        self._run_strategy_flow('均值成本策略', '**/strategy/mean_cost', filler)

    def test_fixed_amount_strategy_gui_backtest_flow(self) -> None:
        def filler(page):
            page.fill("input[name='fixed_amount']", '1000')
            page.select_option("select[name='source']", 'auto')
            page.fill("input[name='lot']", '100')
            page.fill("input[name='cash']", '100000')

        self._run_strategy_flow('定投策略', '**/strategy/fixed_amount', filler)

    def test_a50_strategy_gui_backtest_flow(self) -> None:
        def filler(page):
            page.fill("input[name='futures_symbol']", 'CN00Y')
            page.fill("input[name='base_position_lots']", '2')
            page.select_option("select[name='source']", 'akshare')
            page.fill("input[name='lot']", '100')
            page.fill("input[name='cash']", '100000')

        self._run_strategy_flow('A50 前夜信号(1h)策略', '**/strategy/a50_prev_night_1h', filler)

    def test_signal_template_strategy_gui_backtest_flow(self) -> None:
        def filler(page):
            page.select_option("select[name='buy_trigger']", 'macd_golden')
            page.check("input[name='buy_exec_mode'][value='fixed_amount']")
            page.fill("input[name='buy_fixed_amount']", '20000')

            page.select_option("select[name='sell_trigger']", 'profit_target')
            page.fill("input[name='sell_profit_pct']", '8')
            page.check("input[name='sell_exec_mode'][value='ratio']")
            page.fill("input[name='sell_ratio_pct']", '50')

            page.select_option("select[name='source']", 'auto')
            page.fill("input[name='lot']", '100')
            page.fill("input[name='cash']", '100000')

        self._run_strategy_flow('信号模板策略', '**/strategy/signal_template', filler)


if __name__ == '__main__':
    unittest.main()
