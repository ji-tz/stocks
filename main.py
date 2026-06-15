import os
import sys

# 确保工程根目录在 sys.path，便于导入 sibling 模块
sys.path.insert(0, os.path.dirname(__file__))

import trader.stocks as stocks
from gui import web


def main():
    # 初始化后端（创建缓存目录等）并尝试预热默认数据缓存
    stocks.init()
    try:
        # 仅尝试预热默认 code，不成功也不阻塞启动
        stocks.get_data()
    except Exception:
        pass

    # 启动前端 Flask 应用（由 gui/web.py 提供 `app`）
    web.app.run(debug=True)
 

if __name__ == '__main__':
    main()
