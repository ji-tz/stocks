from gui import web
from trader import persistence
import trader.stocks as stocks
import os
import sys

# 确保工程根目录在 sys.path，便于导入 sibling 模块
sys.path.insert(0, os.path.dirname(__file__))


def main():
    # 初始化持久化层（参数预设 + 回测结果历史）
    persistence.init_db()

    # 初始化后端（创建缓存目录等）并尝试预热默认数据缓存
    stocks.init()
    try:
        # 仅尝试预热默认 code，不成功也不阻塞启动
        stocks.get_data()
    except Exception:
        pass

    # 启动前端 Flask 应用（由 gui/web.py 提供 `app`）
    # debug=True 仅用于开发，生产环境用 env var FLASK_DEBUG=0
    debug_mode = os.environ.get('FLASK_DEBUG', '1').lower() in ('1', 'true', 'yes')
    web.app.run(debug=debug_mode)


if __name__ == '__main__':
    main()
