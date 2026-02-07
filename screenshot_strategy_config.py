#!/usr/bin/env python3
"""
策略配置界面截图脚本
截取三种策略的参数配置页面
"""
import os
import sys
import time
import subprocess
from playwright.sync_api import sync_playwright

# 确保项目根目录在 sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def take_strategy_config_screenshots(output_dir: str = "screenshots", port: int = 5000):
    """启动 Flask 应用，截取三种策略的配置页面"""
    
    # 创建截图目录
    os.makedirs(output_dir, exist_ok=True)
    
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
    max_retries = 20
    for i in range(max_retries):
        try:
            response = requests.get(f"http://127.0.0.1:{port}/", timeout=2)
            if response.status_code == 200:
                print(f"服务器已就绪 (尝试 {i+1}/{max_retries})")
                break
        except Exception as e:
            if i < max_retries - 1:
                time.sleep(2)
            else:
                print(f"警告: 服务器启动失败 - {e}")
                raise Exception("Flask服务器启动超时")
    
    # 额外等待确保页面稳定
    time.sleep(2)
    
    try:
        with sync_playwright() as p:
            # 启动浏览器
            print("启动浏览器...")
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            # 策略列表
            strategies = [
                {
                    'name': 'SMA策略',
                    'url': '/strategy/sma',
                    'filename': 'strategy_sma_config.png',
                    'stock_code': '600900',
                    'stock_name': '长江电力'
                },
                {
                    'name': '均值成本策略',
                    'url': '/strategy/mean_cost',
                    'filename': 'strategy_mean_cost_config.png',
                    'stock_code': '600519',
                    'stock_name': '贵州茅台'
                },
                {
                    'name': '定投策略',
                    'url': '/strategy/fixed_amount',
                    'filename': 'strategy_fixed_amount_config.png',
                    'stock_code': '002594',
                    'stock_name': '比亚迪'
                }
            ]
            
            for strategy in strategies:
                print(f"\n=== 截取 {strategy['name']} 配置页面 ===")
                
                # 先设置session - 通过访问API来设置股票
                print(f"设置股票信息: {strategy['stock_code']} - {strategy['stock_name']}")
                
                # 使用evaluate来设置session通过API
                page.goto(f"http://127.0.0.1:{port}/", wait_until="networkidle", timeout=30000)
                time.sleep(1)
                
                # 通过JavaScript调用API设置股票
                page.evaluate(f"""
                    fetch('/api/select_stock', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{
                            code: '{strategy['stock_code']}',
                            name: '{strategy['stock_name']}'
                        }})
                    }})
                """)
                time.sleep(1)
                
                # 访问策略配置页面
                url = f"http://127.0.0.1:{port}{strategy['url']}"
                print(f"访问: {url}")
                page.goto(url, wait_until="networkidle", timeout=30000)
                
                # 等待页面加载完成
                time.sleep(2)
                
                # 截图
                output_path = os.path.join(output_dir, strategy['filename'])
                print(f"截图保存到: {output_path}")
                page.screenshot(path=output_path, full_page=True)
                print(f"✓ {strategy['name']} 截图完成")
            
            browser.close()
            print("\n所有策略配置页面截图完成!")
            
    except Exception as e:
        print(f"截图失败: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        # 关闭 Flask 服务器
        print("\n关闭 Flask 服务器...")
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
    output_dir = "screenshots"
    if len(sys.argv) > 1:
        output_dir = sys.argv[1]
    
    take_strategy_config_screenshots(output_dir)
