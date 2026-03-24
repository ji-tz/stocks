# stocks.py 索引

- stocks.py 是后端统一外观层，负责日期规范化、数据获取包装、策略注册与统一回测入口。
- BacktestRequest 封装了股票、时间范围、初始资金、交易手数、数据源、交易时点和策略专属参数。
- StrategySpec 与 StrategyParameter 描述策略元数据，当前已注册 sma、mean_cost、fixed_amount 三种策略。
- create_backtest_request 负责统一校验日期、交易手数、资金、交易时点和策略参数。
- run_backtest 按注册表分发到具体策略执行函数，减少 gui/web.py 中的策略分支硬编码。
- run_sma_backtest 已完全基于 simulator.simulate_sma 生成结果，仅保留 final_cash 作为兼容字段，其值等于 total_value。
- 当前注册表将三种策略都限制为 open 成交价，后续若扩展到任意时点，应先放宽对应策略的 supported_trade_prices。