# Stocks - 量化股票回测系统

一个基于 Python 的量化股票回测系统，基于统一模拟交易模型和 AKShare 数据获取，支持 Web 界面操作。

## 技术栈
- Python 3.11+
- Flask (Web GUI)
- pandas, matplotlib (数据处理和图表)
- akshare, baostock (数据源)
- 虚拟环境: .venv/ (source .venv/bin/activate 激活)

## 项目结构
- main.py — 主入口
- stocks.py — 后端业务模块
- gui/web.py — Flask应用
- solver/ — 策略实现 (SMA/均值成本/定投/双均线/布林带/RSI)
- simulator/ — 模拟器框架
- source/ — 数据源
- tests/ — 测试

## 运行方式
- Web界面: source .venv/bin/activate && python main.py
- 命令行回测: source .venv/bin/activate && python run_mean_cost.py
- 测试: source .venv/bin/activate && python -m unittest discover tests -v
