# gui 目录索引

- gui/templates/strategy_fixed_amount.html 的实时计算区域包含每手金额、定投金额是一手金额的整数倍、资金支持手数。
- 定投金额倍数使用 Math.floor(fixedAmount / lotAmount) 计算整数倍。
- 当定投金额不足买入一手时，倍率显示为 0，并通过 warning-text 样式标红。
- tests/guitests/test_realtime_lot_calculation.py 负责校验实时计算区域的关键 DOM 和脚本逻辑。
- gui/templates/select_time_range.html 会根据当前日期选择实时请求 /api/stock_chart/<stock_code>，展示日线开盘价走势图。
- 时间段页的“清除全部缓存并自动重下当前股票日线数据”按钮会调用 /api/stock_chart/<stock_code>/refresh_cache，先清空 data 目录下 CSV 缓存，再重下当前股票日线数据并刷新图表。
- tests/guitests/test_gui_app.py 负责校验时间段页面的走势图与清缓存接口。