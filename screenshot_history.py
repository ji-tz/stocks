#!/usr/bin/env python3
"""
历史记录和对比功能的GUI测试和截图脚本

测试场景：
1. 首页（带历史记录按钮）
2. 空历史记录页面
3. 运行回测并自动保存
4. 包含记录的历史页面
5. 选择记录准备对比
6. 对比页面展示
"""
import os
import sys
import time
import subprocess
from playwright.sync_api import sync_playwright

# 确保项目根目录在 sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_history_and_compare_ui(output_dir: str = "screenshots", port: int = 5000):
    """测试历史记录和对比功能的完整流程"""
    
    # 创建截图目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 启动 Flask 服务器
    print("=" * 80)
    print("启动 Flask 服务器...")
    print("=" * 80)
    flask_process = subprocess.Popen(
        [sys.executable, "-m", "gui.web"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    
    # 等待服务器启动
    print("等待服务器启动...")
    import requests
    max_retries = 15
    for i in range(max_retries):
        try:
            response = requests.get(f"http://127.0.0.1:{port}/", timeout=2)
            if response.status_code == 200:
                print(f"✓ 服务器已就绪 (尝试 {i+1}/{max_retries})")
                break
        except Exception:
            if i < max_retries - 1:
                time.sleep(1)
            else:
                print("⚠ 警告: 服务器可能未完全就绪，继续尝试截图...")
    
    time.sleep(2)
    
    screenshots_taken = []
    
    try:
        with sync_playwright() as p:
            # 启动浏览器
            print("\n" + "=" * 80)
            print("启动浏览器...")
            print("=" * 80)
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 1280, 'height': 800})
            
            base_url = f"http://127.0.0.1:{port}"
            
            # 场景1: 首页（带历史记录按钮）
            print("\n[1/7] 截图：首页（带历史记录按钮）")
            page.goto(f"{base_url}/", wait_until="networkidle", timeout=30000)
            time.sleep(1)
            screenshot_path = os.path.join(output_dir, "01_homepage_with_history_button.png")
            page.screenshot(path=screenshot_path, full_page=True)
            screenshots_taken.append(screenshot_path)
            print(f"  ✓ 保存到: {screenshot_path}")
            
            # 场景2: 空历史记录页面
            print("\n[2/7] 截图：空历史记录页面")
            page.click('text=历史记录')
            page.wait_for_load_state('networkidle')
            time.sleep(1)
            screenshot_path = os.path.join(output_dir, "02_empty_history_page.png")
            page.screenshot(path=screenshot_path, full_page=True)
            screenshots_taken.append(screenshot_path)
            print(f"  ✓ 保存到: {screenshot_path}")
            
            # 场景3: 返回首页，运行第一次回测（均值成本策略）
            print("\n[3/7] 运行回测：均值成本策略")
            page.goto(f"{base_url}/strategy/mean_cost", wait_until="networkidle")
            time.sleep(1)
            
            # 填写表单
            page.fill('input[name="symbol"]', '600900')
            page.fill('input[name="start"]', '20250101')
            page.fill('input[name="end"]', '20250131')
            page.fill('input[name="cash"]', '50000')
            
            # 提交表单
            print("  提交回测请求...")
            page.click('button[type="submit"]')
            page.wait_for_load_state('networkidle', timeout=60000)
            time.sleep(2)
            
            screenshot_path = os.path.join(output_dir, "03_backtest_result_mean_cost.png")
            page.screenshot(path=screenshot_path, full_page=True)
            screenshots_taken.append(screenshot_path)
            print(f"  ✓ 回测完成，保存到: {screenshot_path}")
            
            # 场景4: 查看包含一条记录的历史页面
            print("\n[4/7] 截图：包含一条记录的历史页面")
            page.goto(f"{base_url}/history", wait_until="networkidle")
            time.sleep(1)
            screenshot_path = os.path.join(output_dir, "04_history_with_one_record.png")
            page.screenshot(path=screenshot_path, full_page=True)
            screenshots_taken.append(screenshot_path)
            print(f"  ✓ 保存到: {screenshot_path}")
            
            # 场景5: 运行第二次回测（定投策略）
            print("\n[5/7] 运行回测：定投策略")
            page.goto(f"{base_url}/strategy/fixed_amount", wait_until="networkidle")
            time.sleep(1)
            
            page.fill('input[name="symbol"]', '600900')
            page.fill('input[name="start"]', '20250101')
            page.fill('input[name="end"]', '20250131')
            page.fill('input[name="fixed_amount"]', '1000')
            page.fill('input[name="cash"]', '50000')
            
            print("  提交回测请求...")
            page.click('button[type="submit"]')
            page.wait_for_load_state('networkidle', timeout=60000)
            time.sleep(2)
            
            screenshot_path = os.path.join(output_dir, "05_backtest_result_fixed_amount.png")
            page.screenshot(path=screenshot_path, full_page=True)
            screenshots_taken.append(screenshot_path)
            print(f"  ✓ 回测完成，保存到: {screenshot_path}")
            
            # 场景6: 查看包含两条记录的历史页面，并选择记录
            print("\n[6/7] 截图：包含两条记录的历史页面（选中状态）")
            page.goto(f"{base_url}/history", wait_until="networkidle")
            time.sleep(1)
            
            # 选中两条记录
            checkboxes = page.query_selector_all('.record-checkbox')
            if len(checkboxes) >= 2:
                checkboxes[0].check()
                checkboxes[1].check()
                time.sleep(0.5)
            
            screenshot_path = os.path.join(output_dir, "06_history_records_selected.png")
            page.screenshot(path=screenshot_path, full_page=True)
            screenshots_taken.append(screenshot_path)
            print(f"  ✓ 保存到: {screenshot_path}")
            
            # 场景7: 对比页面
            print("\n[7/7] 截图：对比页面")
            if len(checkboxes) >= 2:
                page.click('#compareBtn')
                page.wait_for_load_state('networkidle', timeout=30000)
                time.sleep(3)  # 等待图表渲染
                
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
        # 关闭 Flask 服务器
        print("\n" + "=" * 80)
        print("关闭 Flask 服务器...")
        print("=" * 80)
        try:
            flask_process.terminate()
            flask_process.wait(timeout=5)
        except Exception as e:
            print(f"⚠ 关闭服务器时出错: {e}")
            try:
                flask_process.kill()
            except Exception:
                pass
    
    # 输出测试总结
    print("\n" + "=" * 80)
    print("✅ GUI测试和截图完成!")
    print("=" * 80)
    print(f"\n共生成 {len(screenshots_taken)} 张截图：")
    for i, path in enumerate(screenshots_taken, 1):
        print(f"  {i}. {path}")
    print()
    
    return screenshots_taken


if __name__ == "__main__":
    output_dir = "screenshots"
    if len(sys.argv) > 1:
        output_dir = sys.argv[1]
    
    test_history_and_compare_ui(output_dir)
