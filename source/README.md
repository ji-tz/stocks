# Source 数据源模块

## 概述

本模块提供统一的股票数据获取接口，支持多个数据源，并实现了数据缓存机制。

## 架构设计

### 类层次结构

```
BaseProvider (抽象基类)
    ├── AkshareProvider (akshare数据源)
    └── BaostockProvider (baostock数据源)
```

### 主要文件

- `base_provider.py`: 定义抽象基类接口
- `akshare_provider.py`: akshare数据源实现
- `baostock_provider.py`: baostock数据源实现
- `data_provider.py`: 统一数据获取接口和缓存管理

## 复权处理

### 什么是复权？

股票在分红、送股、配股等情况下会进行除权除息，导致股价出现"跳空"。复权就是对历史价格进行调整，消除这些非真实的价格变动，确保技术分析和收益计算的准确性。

### 复权类型

1. **前复权（qfq）**: 保持最新价格不变，向前调整历史价格
   - 优点：便于与当前实盘价格对比
   - 使用场景：适合短期交易、实盘对比

2. **后复权（hfq）**: 保持最早价格不变，向后调整价格
   - 优点：保持IPO首日价格真实
   - 使用场景：适合长期投资分析

3. **不复权**: 显示真实的历史交易价格
   - 缺点：无法准确计算收益率
   - 不推荐用于量化回测

### 当前实现

本项目统一使用**前复权（qfq）**：

#### AkshareProvider
```python
df = ak.stock_zh_a_hist(
    symbol=symbol,
    adjust="qfq",  # 前复权
    ...
)
```

参数说明：
- `adjust=""`: 不复权
- `adjust="qfq"`: 前复权
- `adjust="hfq"`: 后复权

#### BaostockProvider
```python
rs = bs.query_history_k_data_plus(
    code,
    adjustflag="2",  # 前复权
    ...
)
```

参数说明：
- `adjustflag="3"`: 不复权
- `adjustflag="2"`: 前复权
- `adjustflag="1"`: 后复权

### 为什么选择前复权？

1. **实盘对比**: 保持最新价格与实盘一致，便于投资决策
2. **直观性**: 当前价格就是真实交易价格，不需要换算
3. **常用性**: 大多数量化平台和交易软件默认使用前复权

## 使用示例

### 基本用法

```python
from source.data_provider import get_data

# 获取股票数据（自动使用前复权）
df = get_data(
    symbol="600900",
    source="akshare",
    start_date="20200101",
    end_date="20231231"
)
```

### 多数据源自动切换

```python
# 自动尝试多个数据源
df = get_data(
    symbol="600900",
    source="auto",  # 自动尝试 akshare -> baostock
    start_date="20200101",
    end_date="20231231"
)
```

## 数据缓存

### 缓存机制

1. 数据首次获取后自动缓存到 `data/{symbol}.csv`
2. 后续请求优先从缓存读取
3. 新数据与缓存自动合并去重
4. 按日期排序保证数据一致性

### 缓存文件格式

CSV格式，包含以下列：
- `date`: 日期（datetime）
- `open`: 开盘价
- `high`: 最高价
- `low`: 最低价
- `close`: 收盘价
- `volume`: 成交量

**注意**: 所有价格均为复权后价格（前复权）。

## 常见问题

### Q: 为什么回测收益与不复权数据计算的不一致？

A: 不复权数据在分红除权时会出现价格"跳空"，导致收益计算错误。使用前复权数据可以消除这种影响，确保收益计算准确。

### Q: 缓存的数据是否会自动更新复权因子？

A: 建议定期删除缓存文件，重新获取数据。因为历史复权因子可能随新的分红而变化。

### Q: 可以切换到后复权吗？

A: 可以，但需要修改两个Provider的复权参数。不建议混用不同复权方式的数据。

## 测试

相关测试位于 `tests/` 目录：
- `test_data_provider_cache.py`: 数据获取和缓存测试
- `test_integration.py`: 集成测试

## 参考资料

- [AKShare 官方文档](https://akshare.akfamily.xyz/)
- [Baostock 官方文档](http://baostock.com/)
- [复权处理说明](https://baike.baidu.com/item/复权)
