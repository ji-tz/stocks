# gui 目录索引

- gui/templates/strategy_fixed_amount.html 的实时计算区域包含每手金额、定投金额是一手金额的整数倍、资金支持手数。
- 定投金额倍数使用 Math.floor(fixedAmount / lotAmount) 计算整数倍。
- 当定投金额不足买入一手时，倍率显示为 0，并通过 warning-text 样式标红。
- tests/guitests/test_realtime_lot_calculation.py 负责校验实时计算区域的关键 DOM 和脚本逻辑。