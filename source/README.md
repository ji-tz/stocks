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

### Q: 什么是"高级接口/付费请求（Premium Requests）"？通过 API 调用是付费的吗？

A: **本项目使用的 akshare 和 baostock 均为免费开源库，调用本身不收费。**

但需要了解以下几点：

1. **akshare 的底层数据来源**：`AkshareProvider` 调用的是[东方财富（East Money）](https://www.eastmoney.com/) 的公开行情 API，该 API 本身是免费的，但并非官方开放接口。

2. **"Premium Requests" 的含义**：在 akshare 生态中，"高级接口"或"premium requests"通常指：
   - **速率限制（Rate Limiting）**：东方财富服务器会对高频请求进行限速，大量短时间内的请求可能被拒绝或返回空数据。
   - **反爬虫机制**：东方财富会检测异常请求（如服务器环境、无 Cookies 等），可能返回空响应或拒绝连接。
   - **访问环境限制**：在 CI/CD 环境（如 GitHub Actions）中，由于 IP 无法解析中国境内域名，akshare 的网络请求通常会失败。

3. **baostock 的情况**：`BaostockProvider` 使用 [baostock](http://baostock.com/) 提供的免费证券数据接口，需要先登录（`bs.login()`）但不需要付费账户。

**总结**：通过 API 调用 akshare/baostock 本身**不产生费用**，但可能因速率限制、反爬虫机制或网络环境而失败。本项目通过以下策略应对这些问题：

- 优先读取本地缓存（`data/{symbol}.csv`），避免不必要的网络请求
- akshare 失败时自动切换到 baostock（`source="auto"` 模式）
- akshare 支持最多 3 次重试（`max_attempts` 参数）

### Q: akshare 请求失败怎么办？

A: 常见原因及解决方案：

| 错误类型 | 原因 | 解决方案 |
|---------|------|---------|
| `ConnectionError` / DNS 解析失败 | 网络环境无法访问东方财富服务器（如 CI 环境） | 使用本地缓存文件，或切换到 baostock |
| `RemoteDisconnected` / 连接中断 | 东方财富反爬虫限速 | 降低请求频率，适当等待后重试 |
| 返回空 DataFrame | 股票代码错误或超出请求限制 | 检查股票代码，使用 `source="auto"` 自动切换 |

建议在无法访问东方财富 API 的环境下（如 CI/CD），使用本地 `data/` 目录中预先缓存的数据文件。

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
