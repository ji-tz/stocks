"""GUI 测试包初始化。

仅提供 Playwright Chromium 的显式安装检查工具，避免在导入任意
guitests 子模块时触发浏览器启动，从而让非浏览器测试保持轻量稳定。
"""

import subprocess
import sys


def _ensure_playwright_chromium():
    """确保 Chromium 浏览器已安装。

    如果第一次运行或者最近更新了 playwright，
    可能需要执行安装命令。我们尝试启动一个临时
    浏览器实例来验证安装；如果检测到缺少可执行文件，
    则自动调用 `playwright install` 和 `playwright install-deps`。
    """
    try:
        # 导入延迟到函数内部，避免在没有安装 playwright 时导入失败
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            # 尝试启动 Chromium 并立即关闭
            browser = p.chromium.launch(headless=True)
            browser.close()
    except Exception as exc:  # pylint: disable=broad-except
        msg = str(exc)
        if "Executable doesn't exist" in msg or 'Please run the following command to download new browsers' in msg:
            # 自动安装所需的浏览器及依赖
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
            subprocess.run([sys.executable, "-m", "playwright", "install-deps", "chromium"], check=True)
        else:
            # 如果是其他错误，则重新抛出
            raise
