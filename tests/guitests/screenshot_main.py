#!/usr/bin/env python3
"""
GUI 截图统一脚本
支持：主界面 / 策略配置 / 历史记录对比
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import subprocess
from typing import Dict, Iterable, List, Optional

from playwright.sync_api import sync_playwright

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
# 确保项目根目录在 sys.path
sys.path.insert(0, ROOT_DIR)

DEFAULT_PORT = 5000
DEFAULT_OUTPUT_DIR = "screenshots"
AVAILABLE_TARGETS = ["main", "strategy", "history"]


def resolve_targets(target: Optional[str], run_all: bool = False) -> List[str]:
    """解析截图目标"""
    if run_all or target in (None, "all"):
        return AVAILABLE_TARGETS.copy()
    if target not in AVAILABLE_TARGETS:
        raise ValueError(f"未知目标: {target}")
    return [target]


def build_output_plan(
    targets: Iterable[str],
    output_dir: str,
    output_main: Optional[str] = None,
) -> Dict[str, str]:
    """构建输出路径规划"""
    plan: Dict[str, str] = {}
    for target in targets:
        if target == "main":
            plan[target] = output_main or os.path.join(output_dir, "main_gui.png")
        elif target in ("strategy", "history"):
            plan[target] = output_dir
    return plan


def _start_flask_server(port: int, max_retries: int = 15, retry_interval: float = 1.0) -> subprocess.Popen:
    """启动 Flask 服务器并等待就绪"""
    flask_process = subprocess.Popen(
        [sys.executable, "-m", "gui.web"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=ROOT_DIR,
    )

    print("等待服务器启动...")
    import requests

    for i in range(max_retries):
        try:
            response = requests.get(f"http://127.0.0.1:{port}/", timeout=2)
            if response.status_code == 200:
                print(f"服务器已就绪 (尝试 {i + 1}/{max_retries})")
                break
        except Exception:
            if i < max_retries - 1:
                time.sleep(retry_interval)
            else:
                print("警告: 服务器可能未完全就绪，继续尝试截图...")

    time.sleep(2)
    return flask_process


def _stop_flask_server(process: subprocess.Popen) -> None:
    """安全关闭 Flask 服务器"""
    print("关闭 Flask 服务器...")
    try:
        process.terminate()
        process.wait(timeout=5)
    except Exception as e:
        print(f"关闭服务器时出错: {e}")
        try:
            process.kill()
        except Exception:
            pass


def _ensure_dir(path: str) -> None:
    if path:
        os.makedirs(path, exist_ok=True)


def _set_stock_session(page, base_url: str, stock_code: str, stock_name: str) -> None:
    page.goto(f"{base_url}/", wait_until="networkidle", timeout=30000)
    time.sleep(1)
    page.evaluate(
        """
        ({ code, name }) => fetch('/api/select_stock', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ code, name })
        })
        """,
        {"code": stock_code, "name": stock_name},
    )
    time.sleep(1)


def take_main_gui_screenshot(output_path: str = "screenshots/main_gui.png", port: int = DEFAULT_PORT) -> str:
    """启动 Flask 应用，打开主界面并截图"""
    _ensure_dir(os.path.dirname(output_path))
    print("启动 Flask 服务器...")
    flask_process = _start_flask_server(port)

    try:
        with sync_playwright() as p:
            print("启动浏览器...")
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 800})

            url = f"http://127.0.0.1:{port}/"
            print(f"访问主页面: {url}")
            page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(2)

            print(f"截图保存到: {output_path}")
            page.screenshot(path=output_path, full_page=True)
            browser.close()
            print("截图完成!")
            return output_path
    except Exception as e:
        print(f"截图失败: {e}")
        raise
    finally:
        _stop_flask_server(flask_process)


def take_strategy_config_screenshots(output_dir: str = "screenshots", port: int = DEFAULT_PORT) -> List[str]:
    """启动 Flask 应用，截取三种策略的配置页面"""
    _ensure_dir(output_dir)
    print("启动 Flask 服务器...")
    flask_process = _start_flask_server(port, max_retries=20, retry_interval=2.0)

    screenshots_taken: List[str] = []

    try:
        with sync_playwright() as p:
            print("启动浏览器...")
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            strategies = [
                {
                    "name": "SMA策略",
                    "url": "/strategy/sma",
                    "filename": "strategy_sma_config.png",
                    "stock_code": "600900",
                    "stock_name": "长江电力",
                },
                {
                    "name": "均值成本策略",
                    "url": "/strategy/mean_cost",
                    "filename": "strategy_mean_cost_config.png",
                    "stock_code": "600519",
                    "stock_name": "贵州茅台",
                },
                {
                    "name": "定投策略",
                    "url": "/strategy/fixed_amount",
                    "filename": "strategy_fixed_amount_config.png",
                    "stock_code": "002594",
                    "stock_name": "比亚迪",
                },
            ]

            base_url = f"http://127.0.0.1:{port}"
            for strategy in strategies:
                print(f"\n=== 截取 {strategy['name']} 配置页面 ===")
                print(f"设置股票信息: {strategy['stock_code']} - {strategy['stock_name']}")
                _set_stock_session(page, base_url, strategy["stock_code"], strategy["stock_name"])

                url = f"{base_url}{strategy['url']}"
                print(f"访问: {url}")
                page.goto(url, wait_until="networkidle", timeout=30000)
                time.sleep(2)

                output_path = os.path.join(output_dir, strategy["filename"])
                print(f"截图保存到: {output_path}")
                page.screenshot(path=output_path, full_page=True)
                screenshots_taken.append(output_path)
                print(f"✓ {strategy['name']} 截图完成")

            browser.close()
            print("\n所有策略配置页面截图完成!")
            return screenshots_taken
    except Exception as e:
        print(f"截图失败: {e}")
        raise
    finally:
        _stop_flask_server(flask_process)


def capture_stock_price_chart(output_path: str = "screenshots/stock_price_chart.png", port: int = DEFAULT_PORT) -> str:
    """
    已废弃：此功能已被移除
    Stock Price Chart 截图功能已从 GUI 测试中删除
    """
    raise NotImplementedError("Stock Price Chart screenshot has been removed from GUI tests")


def test_history_and_compare_ui(output_dir: str = "screenshots", port: int = DEFAULT_PORT) -> List[str]:
    """测试历史记录和对比功能的完整流程"""
    _ensure_dir(output_dir)
    print("启动 Flask 服务器...")
    flask_process = _start_flask_server(port)

    screenshots_taken: List[str] = []

    try:
        with sync_playwright() as p:
            print("\n启动浏览器...")
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 800})

            base_url = f"http://127.0.0.1:{port}"

            print("\n[1/7] 截图：首页（带历史记录按钮）")
            page.goto(f"{base_url}/", wait_until="networkidle", timeout=30000)
            time.sleep(1)
            screenshot_path = os.path.join(output_dir, "01_homepage_with_history_button.png")
            page.screenshot(path=screenshot_path, full_page=True)
            screenshots_taken.append(screenshot_path)
            print(f"  ✓ 保存到: {screenshot_path}")

            print("\n[2/7] 截图：空历史记录页面")
            page.click("text=历史记录")
            page.wait_for_load_state("networkidle")
            time.sleep(1)
            screenshot_path = os.path.join(output_dir, "02_empty_history_page.png")
            page.screenshot(path=screenshot_path, full_page=True)
            screenshots_taken.append(screenshot_path)
            print(f"  ✓ 保存到: {screenshot_path}")

            print("\n[3/7] 运行回测：均值成本策略")
            # 先设置时间段（通过API，等待响应完成）
            page.evaluate("""
                async () => {
                    const response = await fetch('/api/select_time_range', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({start: '20250101', end: '20250131'})
                    });
                    if (!response.ok) {
                        throw new Error('Failed to set time range');
                    }
                    return await response.json();
                }
            """)
            time.sleep(0.5)
            
            page.goto(f"{base_url}/strategy/mean_cost", wait_until="networkidle")
            time.sleep(1)

            # 只填写策略页面实际存在的字段
            page.fill('input[name="cash"]', "50000")

            print("  提交回测请求...")
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle", timeout=60000)
            time.sleep(2)

            screenshot_path = os.path.join(output_dir, "03_backtest_result_mean_cost.png")
            page.screenshot(path=screenshot_path, full_page=True)
            screenshots_taken.append(screenshot_path)
            print(f"  ✓ 回测完成，保存到: {screenshot_path}")

            print("\n[4/7] 截图：包含一条记录的历史页面")
            page.goto(f"{base_url}/history", wait_until="networkidle")
            time.sleep(1)
            screenshot_path = os.path.join(output_dir, "04_history_with_one_record.png")
            page.screenshot(path=screenshot_path, full_page=True)
            screenshots_taken.append(screenshot_path)
            print(f"  ✓ 保存到: {screenshot_path}")

            print("\n[5/7] 运行回测：定投策略")
            # 先设置时间段（通过API，等待响应完成）
            page.evaluate("""
                async () => {
                    const response = await fetch('/api/select_time_range', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({start: '20250101', end: '20250131'})
                    });
                    if (!response.ok) {
                        throw new Error('Failed to set time range');
                    }
                    return await response.json();
                }
            """)
            time.sleep(0.5)
            
            page.goto(f"{base_url}/strategy/fixed_amount", wait_until="networkidle")
            time.sleep(1)

            # 只填写策略页面实际存在的字段
            page.fill('input[name="fixed_amount"]', "1000")
            page.fill('input[name="cash"]', "50000")

            print("  提交回测请求...")
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle", timeout=60000)
            time.sleep(2)

            screenshot_path = os.path.join(output_dir, "05_backtest_result_fixed_amount.png")
            page.screenshot(path=screenshot_path, full_page=True)
            screenshots_taken.append(screenshot_path)
            print(f"  ✓ 回测完成，保存到: {screenshot_path}")

            print("\n[6/7] 截图：包含两条记录的历史页面（选中状态）")
            page.goto(f"{base_url}/history", wait_until="networkidle")
            time.sleep(1)

            checkboxes = page.query_selector_all(".record-checkbox")
            if len(checkboxes) >= 2:
                checkboxes[0].check()
                checkboxes[1].check()
                time.sleep(0.5)

            screenshot_path = os.path.join(output_dir, "06_history_records_selected.png")
            page.screenshot(path=screenshot_path, full_page=True)
            screenshots_taken.append(screenshot_path)
            print(f"  ✓ 保存到: {screenshot_path}")

            print("\n[7/7] 截图：对比页面")
            if len(checkboxes) >= 2:
                page.click("#compareBtn")
                page.wait_for_load_state("networkidle", timeout=30000)
                time.sleep(3)

                screenshot_path = os.path.join(output_dir, "07_compare_page_with_charts.png")
                page.screenshot(path=screenshot_path, full_page=True)
                screenshots_taken.append(screenshot_path)
                print(f"  ✓ 保存到: {screenshot_path}")
            else:
                print("  ⚠ 跳过对比页面（记录不足）")

            browser.close()

    except Exception as e:
        print(f"\n❌ 测试过程中出错: {e}")
        import traceback

        traceback.print_exc()
        raise
    finally:
        _stop_flask_server(flask_process)

    print("\n" + "=" * 80)
    print("✅ GUI测试和截图完成!")
    print("=" * 80)
    print(f"\n共生成 {len(screenshots_taken)} 张截图：")
    for i, path in enumerate(screenshots_taken, 1):
        print(f"  {i}. {path}")
    print()

    return screenshots_taken


def run_targets(
    targets: Iterable[str],
    output_plan: Dict[str, str],
    port: int = DEFAULT_PORT,
) -> None:
    """按目标顺序执行截图任务"""
    ordered_targets = [t for t in AVAILABLE_TARGETS if t in set(targets)]
    for target in ordered_targets:
        if target == "main":
            take_main_gui_screenshot(output_plan[target], port=port)
        elif target == "strategy":
            take_strategy_config_screenshots(output_plan[target], port=port)
        elif target == "history":
            test_history_and_compare_ui(output_plan[target], port=port)


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GUI 截图统一脚本")
    parser.add_argument(
        "target",
        nargs="?",
        choices=AVAILABLE_TARGETS + ["all"],
        default="main",
        help="截图目标（默认：main）",
    )
    parser.add_argument("-o", "--output", help="输出文件路径（仅 main/chart 生效）")
    parser.add_argument("-d", "--output-dir", help="输出目录（默认：screenshots）")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Flask 端口")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) == 1 and not argv[0].startswith("-") and argv[0] not in AVAILABLE_TARGETS + ["all"]:
        args = _parse_args([])
        args.target = "main"
        args.output = argv[0]
    else:
        args = _parse_args(argv)

    output_dir = args.output_dir or DEFAULT_OUTPUT_DIR
    targets = resolve_targets(args.target, run_all=args.target == "all")
    output_plan = build_output_plan(targets, output_dir, output_main=args.output)
    run_targets(targets, output_plan, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
