# solver 目录索引

- solver 目录存放纯策略决策逻辑，当前包含 sma、mean_cost、fixed_amount 三种策略。
- MeanCostDecision 与 FixedAmountDecision 都遵循 Simulator 的 decide 协议，可直接复用统一模拟器。
- SmaDecision 依赖调用方预先在 DataFrame 中生成 sma 列；SMA 已完全走统一模拟器执行链路，项目依赖与 CI 安装链路中也已移除 backtrader。
- 新增策略时，优先保持 solver 只负责决策，把通用回测参数和策略专属参数注册放在 stocks.py 中统一管理。