#!/usr/bin/env python3
"""
主界面截图脚本
使用 playwright 启动浏览器，访问 Flask 应用主界面并截图
"""
import os
import sys
import time
import subprocess
from playwright.sync_api import sync_playwright

# 确保项目根目录在 sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def take_main_gui_screenshot(output_path: str = "screenshots/main_gui.png", port: int = 5000):
    """启动 Flask 应用，打开主界面并截图"""
    
    # 创建截图目录
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 启动 Flask 服务器
    print("启动 Flask 服务器...")
    flask_process = subprocess.Popen(
        [sys.executable, "-m", "gui.web"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    
    # 等待服务器启动
    print("等待服务器启动...")
    import requests
    max_retries = 10
    for i in range(max_retries):
        try:
            response = requests.get(f"http://127.0.0.1:{port}/", timeout=2)
            if response.status_code == 200:
                print(f"服务器已就绪 (尝试 {i+1}/{max_retries})")
                break
        except Exception:
            if i < max_retries - 1:
                time.sleep(1)
            else:
                print("警告: 服务器可能未完全就绪，继续尝试截图...")
    
    # 额外等待确保页面稳定
    time.sleep(2)
    
    try:
        with sync_playwright() as p:
            # 启动浏览器
            print("启动浏览器...")
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # 访问主页面
            url = f"http://127.0.0.1:{port}/"
            print(f"访问主页面: {url}")
            page.goto(url, wait_until="networkidle", timeout=30000)
            
            # 等待页面加载完成
            time.sleep(2)
            
            # 截图
            print(f"截图保存到: {output_path}")
            page.screenshot(path=output_path, full_page=True)
            
            browser.close()
            print("截图完成!")
            
    except Exception as e:
        print(f"截图失败: {e}")
        raise
    finally:
        # 关闭 Flask 服务器
        print("关闭 Flask 服务器...")
        try:
            flask_process.terminate()
            flask_process.wait(timeout=5)
        except Exception as e:
            print(f"关闭服务器时出错: {e}")
            try:
                flask_process.kill()
            except Exception:
                pass


if __name__ == "__main__":
    output = "screenshots/main_gui.png"
    if len(sys.argv) > 1:
        output = sys.argv[1]
    
    take_main_gui_screenshot(output)
