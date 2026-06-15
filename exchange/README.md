# Exchange — 交易所层

交易所层（`exchange/`）是项目的数据与交易核心，提供行情数据获取、交易执行和账户管理三大能力。

## 目录结构

```
exchange/
├── __init__.py              包入口
├── base_engine.py           交易所基类
├── exchange_interface.py    交易接口定义（buy/sell）
├── simulated_exchange.py    回测交易所实现
├── real_engine.py           实盘引擎
├── backtest/exchange.py     回测交易逻辑
├── live/exchange.py         实盘交易逻辑
├── realtime/exchange.py     实时行情订阅
└── source/                  数据源 Provider
    ├── base_provider.py     数据源基类
    ├── data_provider.py     统一数据入口
    ├── provider_utils.py    数据工具函数
    ├── akshare_provider.py  AKShare 数据源
    ├── baostock_provider.py Baostock 数据源
    ├── tencent_provider.py  腾讯数据源
    ├── sina_provider.py     新浪数据源
    ├── sohu_provider.py     搜狐数据源
    ├── eastmoney_provider.py 东方财富数据源
    ├── cailianpress_provider.py 财联社数据源
    └── stooq_provider.py    Stooq 国际数据源
```

## 三层协作定位

```
STRAT → 出买卖信号
  │
  ▼
TRADER → 推时间、读信号、操作
  │
  ▼
EXCH → 提供行情 + 执行交易 + 管账本
```

EXCH 只负责"市场"能力，不关心买卖时机（那是 TRADER 的事），也不关心策略公式（那是 STRAT 的事）。

## 核心接口

- `get_data(symbol, start, end)` → DataFrame — 给 TRADER 和 STRAT 用
- `StockExchange.buy(date, price, shares)` → TradeResult
- `StockExchange.sell(date, price, shares)` → TradeResult
- `Account.get_position()` → 当前持仓
- `Account.get_total_value(price)` → 总资产估值

## Owner

EXCH 角色负责本目录全部文件。详见 `AGENTS.md`。
