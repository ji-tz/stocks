# source 目录索引

- source/data_provider.py 统一封装缓存读取、缓存合并、数据源选择和失败回退。
- stocks.get_data 会在 provider 返回后再按请求时间段做一次过滤，确保上层传入的日期范围最终生效。
- 当前缓存粒度按股票代码存放在 data/{symbol}.csv，时间段过滤发生在读取层而不是缓存文件拆分层。
- data_provider.get_data 现支持 force_refresh 和 buffer_days：强制重建缓存时会绕过旧缓存；按时间段请求时会额外下载前后缓冲天数的数据，再裁剪返回用户请求区间。
- 清缓存并重下当前股票数据的 GUI 能力通过 gui/web.py 中的 _clear_all_cache_files 与 stocks.get_data 组合实现。