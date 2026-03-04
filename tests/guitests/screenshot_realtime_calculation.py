"""截图脚本：策略参数配置页面实时计算功能

生成策略参数配置页面的截图，展示每手金额和资金支持手数的实时计算功能。
使用模拟数据快速生成截图。
"""
import sys
import os
import time
from unittest.mock import patch
import pandas as pd
from playwright.sync_api import sync_playwright

# Ensure Playwright browsers are available (similar logic to other scripts)
try:
    import tests.guitests
except ImportError:
    subprocess.run([sys.executable, '-m', 'playwright', 'install', 'chromium'], check=True)
    subprocess.run([sys.executable, '-m', 'playwright', 'install-deps', 'chromium'], check=True)

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from gui.web import app
import stocks


def create_mock_data():
    """创建模拟数据用于截图"""
    dates = pd.date_range(end='2024-01-10', periods=100)
    return pd.DataFrame({
        'date': dates,
        'open': [15.0 + i * 0.1 for i in range(100)],
        'high': [15.5 + i * 0.1 for i in range(100)],
        'low': [14.5 + i * 0.1 for i in range(100)],
        'close': [15.2 + i * 0.1 for i in range(100)],
        'volume': [10000 + i * 100 for i in range(100)]
    })


def start_app_with_mock():
    """启动Flask应用并mock数据获取"""
    # Mock get_data to avoid real data fetching
    mock_data = create_mock_data()

    original_get_data = stocks.get_data

    def mock_get_data(*args, **kwargs):
        return mock_data

    stocks.get_data = mock_get_data

    import threading
    thread = threading.Thread(
        target=lambda: app.run(port=5556, debug=False, use_reloader=False),
        daemon=True
    )
    thread.start()
    time.sleep(2)  # 等待服务启动

    return original_get_data


def take_screenshots(output_dir='screenshots'):
    """生成策略参数配置页面的截图"""
    os.makedirs(output_dir, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1200, 'height': 1800})

        # 1. 截取SMA策略页面
        print("正在截取 SMA 策略配置页面...")
        page = context.new_page()

        # 直接访问URL，然后手动设置cookie
        page.goto('http://127.0.0.1:5556/')

        # 使用JavaScript注入session数据（通过修改cookie）
        # 先获取一个有效的session
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
                    body: JSON.stringify({strategy_type: 'sma', strategy_name: 'SMA 策略'})
                });
                await fetch('/api/select_mode', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({mode: 'backtest'})
                });
                await fetch('/api/select_time_range', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({start: '', end: ''})
                });
            }
        """)

        time.sleep(0.5)

        # 现在访问策略页面
        page.goto('http://127.0.0.1:5556/strategy/sma')
        time.sleep(2.5)  # 等待页面加载和实时计算API调用完成

        # 滚动到实时计算区域
        page.evaluate("document.getElementById('realtime-info').scrollIntoView({behavior: 'smooth', block: 'center'})")
        time.sleep(0.5)

        # 截取整个页面
        page.screenshot(path=f'{output_dir}/strategy_sma_realtime_calculation.png', full_page=True)
        print(f"✓ 已保存: {output_dir}/strategy_sma_realtime_calculation.png")

        page.close()

        # 2. 截取均值成本策略页面
        print("正在截取均值成本策略配置页面...")
        page2 = context.new_page()

        page2.goto('http://127.0.0.1:5556/')
        page2.evaluate("""
            async () => {
                await fetch('/api/select_stock', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({code: '600519', name: '贵州茅台'})
                });
                await fetch('/api/select_strategy', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({strategy_type: 'mean_cost', strategy_name: '均值成本策略'})
                });
                await fetch('/api/select_mode', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({mode: 'backtest'})
                });
            }
        """)
        time.sleep(0.5)

        page2.goto('http://127.0.0.1:5556/strategy/mean_cost')
        time.sleep(2.5)

        # 修改参数以显示不同的计算结果
        page2.fill('#cash', '200000')
        page2.fill('#lot', '200')
        time.sleep(1)

        page2.evaluate("document.getElementById('realtime-info').scrollIntoView({behavior: 'smooth', block: 'center'})")
        time.sleep(0.5)

        page2.screenshot(path=f'{output_dir}/strategy_mean_cost_realtime_calculation.png', full_page=True)
        print(f"✓ 已保存: {output_dir}/strategy_mean_cost_realtime_calculation.png")

        page2.close()

        # 3. 截取定投策略页面
        print("正在截取定投策略配置页面...")
        page3 = context.new_page()

        page3.goto('http://127.0.0.1:5556/')
        page3.evaluate("""
            async () => {
                await fetch('/api/select_stock', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({code: '000001', name: '平安银行'})
                });
                await fetch('/api/select_strategy', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({strategy_type: 'fixed_amount', strategy_name: '定投策略'})
                });
                await fetch('/api/select_mode', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({mode: 'backtest'})
                });
            }
        """)
        time.sleep(0.5)

        page3.goto('http://127.0.0.1:5556/strategy/fixed_amount')
        time.sleep(2.5)

        # 修改参数
        page3.fill('#cash', '30000')
        time.sleep(1)

        page3.evaluate("document.getElementById('realtime-info').scrollIntoView({behavior: 'smooth', block: 'center'})")
        time.sleep(0.5)

        page3.screenshot(path=f'{output_dir}/strategy_fixed_amount_realtime_calculation.png', full_page=True)
        print(f"✓ 已保存: {output_dir}/strategy_fixed_amount_realtime_calculation.png")

        browser.close()

    print("\n所有截图已生成完成！")
    print(f"截图保存在: {output_dir}/")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='生成策略参数配置页面截图')
    parser.add_argument('--output-dir', default='screenshots', help='截图输出目录')
    args = parser.parse_args()

    print("启动应用（使用模拟数据）...")
    original_get_data = start_app_with_mock()

    print("开始生成截图...")
    try:
        take_screenshots(args.output_dir)
    except Exception as e:
        print(f"错误：{e}")
        import traceback
        traceback.print_exc()
    finally:
        # 恢复原始函数
        if original_get_data:
            stocks.get_data = original_get_data


