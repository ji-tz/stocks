"""
截图脚本：时间段设置功能
生成时间段设置页面的各种状态截图
"""
import sys
import time
import subprocess
import os
from playwright.sync_api import sync_playwright

# 确保 Playwright 浏览器已安装
# 若从包内部调用，导入 tests.guitests 会触发 __init__ 中的检查；
# 如果脚本作为顶层运行，尝试导入可能失败，此时手动安装。
try:
    import tests.guitests  # triggers auto-install helper
except ImportError:
    subprocess.run([sys.executable, '-m', 'playwright', 'install', 'chromium'], check=True)
    subprocess.run([sys.executable, '-m', 'playwright', 'install-deps', 'chromium'], check=True)


def take_time_range_screenshots(output_dir='screenshots'):
    """生成时间段设置功能的截图"""
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 启动Flask服务
    server_process = subprocess.Popen(
        [sys.executable, '-m', 'gui.web'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={**os.environ, 'FLASK_ENV': 'production'}
    )
    
    try:
        # 等待服务器启动
        time.sleep(3)
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 1200, 'height': 900})
            
            try:
                print("📸 开始截图流程...")
                
                # 1. 使用真实的浏览器交互设置session（与test_gui_workflow_e2e.py保持一致）
                print("  - 设置session...")
                page.goto('http://127.0.0.1:5000/', wait_until='networkidle')
                
                # 选择股票
                page.fill("#search-input", "600900")
                page.click("form#search-form button[type='submit']")
                page.wait_for_selector("#result-section.show", timeout=10000)
                page.click("button:has-text('选择此股票')")
                page.wait_for_url("**/select_strategy", timeout=10000)
                
                # 选择策略
                page.click(".strategy-card:has-text('SMA')")
                page.wait_for_url("**/select_mode", timeout=10000)
                
                # 选择回测模式
                page.click(".mode-card.backtest")
                page.wait_for_url("**/select_time_range", timeout=10000)
                
                print("  - Session设置完成，进入时间段选择页面")
                time.sleep(0.5)
                
                # 2. 截图：时间段设置页面（空白状态）
                print("  - 截图：时间段设置页面（空白）...")
                page.goto('http://127.0.0.1:5000/select_time_range', wait_until='networkidle')
                time.sleep(1)
                page.screenshot(path=f'{output_dir}/time_range_01_blank.png')
                
                # 3. 截图：填写日期后
                print("  - 截图：填写日期后...")
                page.fill('input#start-date', '2023-01-01')
                time.sleep(0.2)
                page.fill('input#end-date', '2023-12-31')
                time.sleep(0.5)
                page.screenshot(path=f'{output_dir}/time_range_02_filled.png')
                
                # 4. 截图：点击"最近1年"按钮后
                print("  - 截图：使用快捷按钮...")
                page.click('button:has-text("最近1年")')
                time.sleep(0.5)
                page.screenshot(path=f'{output_dir}/time_range_03_preset_1year.png')
                
                # 5. 截图：点击"最近3年"按钮后
                print("  - 截图：使用快捷按钮（3年）...")
                page.click('button:has-text("最近3年")')
                time.sleep(0.5)
                page.screenshot(path=f'{output_dir}/time_range_04_preset_3years.png')
                
                # 6. 截图：点击"今年至今"按钮后
                print("  - 截图：使用快捷按钮（今年至今）...")
                page.click('button:has-text("今年至今")')
                time.sleep(0.5)
                page.screenshot(path=f'{output_dir}/time_range_05_preset_ytd.png')
                
                # 7. 截图：日期验证错误
                print("  - 截图：日期验证错误...")
                page.fill('input#start-date', '2023-12-31')
                page.fill('input#end-date', '2023-01-01')
                time.sleep(0.5)
                page.screenshot(path=f'{output_dir}/time_range_06_validation_error.png')
                
                # 8. 截图：提交后的策略配置页面（验证时间段已移除）
                print("  - 截图：策略配置页面（已移除时间段）...")
                # 先设置正确的日期
                page.fill('input#start-date', '2023-01-01')
                page.fill('input#end-date', '2023-12-31')
                # 使用真实的表单提交
                page.click("form#timeRangeForm button[type='submit']")
                page.wait_for_url("**/strategy/sma", timeout=10000)
                time.sleep(1)
                page.screenshot(path=f'{output_dir}/time_range_07_strategy_no_dates.png')
                
                print(f"\n✅ 截图完成！共生成 7 张截图，保存在 {output_dir}/ 目录")
                print("\n生成的截图：")
                print("  1. time_range_01_blank.png - 时间段设置页面（空白）")
                print("  2. time_range_02_filled.png - 手动填写日期")
                print("  3. time_range_03_preset_1year.png - 快捷按钮：最近1年")
                print("  4. time_range_04_preset_3years.png - 快捷按钮：最近3年")
                print("  5. time_range_05_preset_ytd.png - 快捷按钮：今年至今")
                print("  6. time_range_06_validation_error.png - 日期验证错误")
                print("  7. time_range_07_strategy_no_dates.png - 策略配置页面（已移除日期输入）")
                
            except Exception as e:
                print(f"❌ 截图失败: {e}", file=sys.stderr)
                page.screenshot(path=f'{output_dir}/error_screenshot.png')
                raise
            finally:
                browser.close()
                
    finally:
        # 关闭Flask服务
        server_process.terminate()
        server_process.wait(timeout=5)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='生成时间段设置功能的截图')
    parser.add_argument('--output-dir', '-o', default='screenshots', help='截图输出目录')
    args = parser.parse_args()
    
    take_time_range_screenshots(args.output_dir)
