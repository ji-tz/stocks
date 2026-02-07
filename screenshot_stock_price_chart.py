#!/usr/bin/env python3
"""
截取股价波动线功能展示图
用于CI/CD工作流自动化测试
"""
import sys
import os
import asyncio
from playwright.async_api import async_playwright
import subprocess
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def capture_stock_price_chart(output_path: str):
    """截取复盘界面的股价波动线图表"""
    
    # 启动Web服务（禁用debug模式和reloader）
    print("🚀 启动Web服务...")
    web_process = subprocess.Popen(
        [sys.executable, '-c', 
         'from gui.web import app; app.run(debug=False, use_reloader=False)'],
        cwd=os.path.dirname(os.path.abspath(__file__)),
        stdout=subprocess.DEVNULL,  # 避免输出阻塞
        stderr=subprocess.DEVNULL
    )
    
    # 等待服务启动
    print("⏳ 等待服务启动...")
    await asyncio.sleep(10)
    
    browser = None
    try:
        async with async_playwright() as p:
            print("🌐 启动浏览器...")
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={'width': 1400, 'height': 900}
            )
            page = await context.new_page()
            
            try:
                # 访问首页，增加重试逻辑
                print("📄 访问首页...")
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        await page.goto('http://127.0.0.1:5000/', wait_until='networkidle', timeout=30000)
                        break
                    except Exception as e:
                        if attempt < max_retries - 1:
                            print(f"⚠️ 尝试 {attempt + 1} 失败，等待重试...")
                            await asyncio.sleep(5)
                        else:
                            raise
                
                # 点击均值成本策略
                print("🎯 进入均值成本策略页面...")
                await page.click('text=均值成本策略')
                await page.wait_for_load_state('networkidle')
                
                # 填写表单 - 使用长江电力数据
                print("📝 填写回测参数...")
                await page.fill('input[name="symbol"]', '600900')
                await page.fill('input[name="start"]', '20230101')
                await page.fill('input[name="end"]', '20230331')  # 3个月数据足够展示
                await page.fill('input[name="cash"]', '100000')
                
                # 提交表单
                print("▶️ 提交回测...")
                await page.click('button[type="submit"]')
                
                # 等待结果页面加载
                print("⏳ 等待回测完成...")
                await page.wait_for_url('**/run', timeout=60000)
                await page.wait_for_load_state('networkidle')
                
                # 等待图表渲染
                print("📊 等待图表渲染...")
                await page.wait_for_selector('canvas#chart', state='visible', timeout=10000)
                await asyncio.sleep(3)  # 额外等待确保Chart.js完全渲染
                
                # 滚动到图表位置
                await page.evaluate("document.querySelector('canvas#chart').scrollIntoView({behavior: 'smooth', block: 'center'})")
                await asyncio.sleep(1)
                
                # 截取图表区域（包含标题和图例）
                print("📸 截取图表区域...")
                chart_element = await page.query_selector('canvas#chart')
                if not chart_element:
                    print("❌ 未找到图表元素")
                    return False
                
                box = await chart_element.bounding_box()
                if not box:
                    print("❌ 无法获取图表位置")
                    return False
                
                # 确保输出目录存在
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # 扩展截图区域以包含标题
                await page.screenshot(
                    path=output_path,
                    clip={
                        'x': max(0, box['x'] - 20),
                        'y': max(0, box['y'] - 80),  # 向上扩展包含"资产曲线"标题
                        'width': min(box['width'] + 40, 1400),
                        'height': min(box['height'] + 100, 900)
                    }
                )
                print(f"✅ 截图已保存: {output_path}")
                return True
                
            finally:
                # 确保浏览器资源被清理
                await context.close()
                if browser:
                    await browser.close()
            
    finally:
        # 停止Web服务（带超时控制）
        print("🛑 停止Web服务...")
        web_process.terminate()
        try:
            web_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("⚠️ 进程未响应，强制终止...")
            web_process.kill()
            web_process.wait()


def main():
    parser = argparse.ArgumentParser(description='截取股价波动线功能展示图')
    parser.add_argument('output', help='输出文件路径')
    args = parser.parse_args()
    
    try:
        success = asyncio.run(capture_stock_price_chart(args.output))
        if success:
            print(f"\n✅ 股价波动线截图生成成功: {args.output}")
            sys.exit(0)
        else:
            print("\n❌ 截图生成失败")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
