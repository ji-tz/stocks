import logging
import subprocess
from gui import web
from trader import persistence
import trader.stocks as stocks
import os
import sys

logger = logging.getLogger(__name__)

# 确保工程根目录在 sys.path，便于导入 sibling 模块
sys.path.insert(0, os.path.dirname(__file__))


def get_version_info() -> str:
    """从 git 自动读取当前 commit 和提交时间，返回版本信息字符串。"""
    try:
        repo_dir = os.path.dirname(os.path.abspath(__file__))
        commit = subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'],
            cwd=repo_dir, stderr=subprocess.DEVNULL
        ).decode().strip()
        date = subprocess.check_output(
            ['git', 'log', '-1', '--format=%ci'],
            cwd=repo_dir, stderr=subprocess.DEVNULL
        ).decode().strip()
        # 尝试获取 tag 版本号
        version = subprocess.check_output(
            ['git', 'describe', '--tags', '--always'],
            cwd=repo_dir, stderr=subprocess.DEVNULL
        ).decode().strip()
        if version == commit:
            return f"Version: {commit} ({date[:10]})"
        return f"Version: {version} (commit {commit}, {date[:10]})"
    except Exception:
        return "Version: unknown (not a git repository)"


def main():
    print(f"\n=== {get_version_info()} ===\n")

    # 初始化持久化层（参数预设 + 回测结果历史）
    persistence.init_db()

    # 初始化后端（创建缓存目录等）并尝试预热默认数据缓存
    stocks.init()
    try:
        # 仅尝试预热默认 code，不成功也不阻塞启动
        stocks.get_data()
    except Exception:
        logger.warning("数据预热失败", exc_info=True)

    # 启动前端 Flask 应用（由 gui/web.py 提供 `app`）
    # debug=True 仅用于开发，生产环境用 env var FLASK_DEBUG=0
    debug_mode = os.environ.get('FLASK_DEBUG', '1').lower() in ('1', 'true', 'yes')
    web.app.run(debug=debug_mode)


if __name__ == '__main__':
    main()
