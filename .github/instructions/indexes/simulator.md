# simulator 目录索引

- simulator/simulator.py 的 Simulator 是统一回测循环，负责按日遍历数据、调用策略 decide、通过 SimulatorEngine 执行成交。
- Simulator.simulate 已支持通过 trade_price 参数选择成交字段，当前默认 open，返回结果中会带上 trade_price_field。
- simulator/simulator_engine.py 负责账户、持仓、盈亏和交易次数统计，不关心策略来源。
- simulator/base_engine.py 定义 Position、Account、TradeOrder、TradeResult 等通用结构，适合作为后续扩展实盘或更多成交模型的稳定边界。
- simulator/base_engine.py 与 simulator/simulator_engine.py 现支持小数份额（shares/lot_size 为 float），可用于基金按份额粒度交易。