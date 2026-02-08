"""GUI进度条截图脚本

测试回测进度条的显示效果
"""
import os
import sys
import subprocess
import time
import signal
from playwright.sync_api import sync_playwright

# 添加项目根目录到path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def start_web_server():
    """启动Flask Web服务"""
    # 创建启动脚本
    script_content = """
import sys
import os
sys.path.insert(0, os.getcwd())
from gui.web import app
app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
"""
    
    script_path = '/tmp/start_flask.py'
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    proc = subprocess.Popen(
        [sys.executable, script_path],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # 等待服务启动，检查输出
    print("等待Flask服务启动...")
    start_time = time.time()
    while time.time() - start_time < 10:
        # 尝试连接
        try:
            import urllib.request
            urllib.request.urlopen('http://127.0.0.1:5000/', timeout=1)
            print("Flask服务启动成功！")
            return proc
        except:
            time.sleep(0.5)
    
    # 如果超时，打印输出并退出
    print("Flask服务启动超时，检查输出：")
    if proc.poll() is None:
        proc.terminate()
        output, _ = proc.communicate(timeout=2)
        print(output)
    raise RuntimeError("Flask服务启动失败")



def take_progress_screenshots(output_dir='screenshots'):
    """截取进度条界面"""
    os.makedirs(output_dir, exist_ok=True)
    
    web_proc = None
    browser = None
    
    try:
        # 启动Web服务
        print("启动Web服务...")
        web_proc = start_web_server()
        
        # 启动浏览器
        print("启动浏览器...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={'width': 1280, 'height': 1024})
            page = context.new_page()
            
            try:
                # 1. 访问首页
                print("访问首页...")
                page.goto('http://127.0.0.1:5000/', timeout=10000)
                page.wait_for_load_state('networkidle', timeout=10000)
                
                # 2. 搜索并选择股票
                print("选择股票...")
                page.fill('input[name="query"]', '600900')
                page.click('button:has-text("搜索")')
                time.sleep(1)
                
                # 点击选择按钮
                page.click('button:has-text("选择此股票")')
                page.wait_for_load_state('networkidle', timeout=5000)
                
                # 3. 选择策略
                print("选择策略...")
                page.click('.strategy-card:has-text("SMA")')
                page.wait_for_load_state('networkidle', timeout=5000)
                
                # 4. 选择运行模式
                print("选择运行模式...")
                page.click('.mode-card:has-text("回测仿真")')
                page.wait_for_load_state('networkidle', timeout=5000)
                
                # 5. 配置策略参数
                print("配置策略参数...")
                page.fill('input[name="start"]', '20230101')
                page.fill('input[name="end"]', '20230131')
                
                # 6. 提交表单，触发回测
                print("提交表单...")
                page.click('button[type="submit"]')
                
                # 等待进度页面加载
                page.wait_for_selector('.progress-bar', timeout=10000)
                time.sleep(0.5)
                
                # 7. 截取初始进度状态（0%）
                print("截取初始进度...")
                page.screenshot(path=f'{output_dir}/progress_initial.png', full_page=True)
                
                # 8. 等待一段时间，截取进行中的状态
                print("等待进度更新...")
                time.sleep(2)
                page.screenshot(path=f'{output_dir}/progress_running.png', full_page=True)
                
                # 9. 等待完成
                print("等待回测完成...")
                completed = page.wait_for_selector(
                    '#status-completed:not(.hidden)',
                    timeout=30000
                )
                
                if completed:
                    time.sleep(0.5)
                    page.screenshot(path=f'{output_dir}/progress_completed.png', full_page=True)
                    print("截取完成状态...")
                    
                    # 10. 点击查看结果按钮
                    print("点击查看结果...")
                    page.click('#view-result-btn')
                    page.wait_for_load_state('networkidle', timeout=10000)
                    time.sleep(1)
                    
                    # 11. 截取结果页面
                    print("截取结果页面...")
                    page.screenshot(path=f'{output_dir}/progress_result.png', full_page=True)
                
                print(f"\n✓ 截图完成！保存在 {output_dir}/ 目录")
                print(f"  - progress_initial.png: 初始进度（0%）")
                print(f"  - progress_running.png: 进行中")
                print(f"  - progress_completed.png: 完成状态（100%）")
                print(f"  - progress_result.png: 回测结果页面")
                
            except Exception as e:
                print(f"✗ 截图失败: {e}")
                # 尝试截取错误状态
                try:
                    page.screenshot(path=f'{output_dir}/progress_error.png', full_page=True)
                    print(f"  保存了错误状态截图: {output_dir}/progress_error.png")
                except:
                    pass
                raise
            finally:
                context.close()
                browser.close()
    
    finally:
        # 清理Web服务进程
        if web_proc:
            print("\n关闭Web服务...")
            try:
                web_proc.send_signal(signal.SIGTERM)
                web_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                web_proc.kill()
                web_proc.wait()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='截取回测进度条界面')
    parser.add_argument('--output-dir', default='screenshots', help='输出目录')
    
    args = parser.parse_args()
    
    take_progress_screenshots(args.output_dir)
