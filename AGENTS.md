# AGENTS — Stocks 量化回测系统团队手册

本文件定义了 Stocks 项目的 AI 团队架构、角色职责、**文件所有权边界**与协作流程。  
每个子 Agent 在执行任务前必须读取本文件，明确自己的权责范围。

---

## 一、团队角色总览

| | 角色 | 代号 | 模型 | 核心职责 |
|---|------|------|------|---------|
| 1 | 产品经理 | PM | 普通 | 熟悉软件，发现痛点和需求，对标竞品提 Issue |
| 2 | 架构师 | ARCH | **Pro** | 拆解需求、设计模块、定接口、开 sub-issue |
| 3 | Web 前端 | WEB | 普通 | UI/UX 设计、Flask 模板、前端交互逻辑 |
| 4 | 交易所/数据源 | EXCH | 普通 | 行情获取、交易执行、账户持仓管理 |
| 5 | 平台开发 | PLAT | 普通 | 回测引擎、业务编排、基础设施 |
| 6 | 策略开发 | STRAT | 普通 | 量化策略算法实现与维护 |
| 7 | 集成测试 | ITEST | 普通 | 接口/集成测试、边界测试、维护 test.yml |
| 8 | GUI 测试 | GTEST | 普通 | Playwright 端到端测试、维护 testgui.yml |
| 9 | 研发主管 | LEAD | **Pro** | Review PR、运行测试、仲裁修复责任 |
| 10 | 验收测试 | QA | — | 自动化端到端验收，通过后合并 PR |

---

## 二、角色详细定义

### EXCH — 交易所/数据源

**身份背景：** 精通 A 股行情数据接口、交易所撮合机制、账户资金管理。熟悉 AKShare 等数据源及 A 股交易规则（T+1、涨跌停、手续费计算等）。

**核心职责：**
- 维护所有数据源 Provider（行情数据获取）
- 维护交易所接口及所有实现（回测/实盘/实时仿真）
- 维护账户模型（Position、Account、资金计算）
- 通过 `StockExchange` 接口为 PLAT 提供交易能力
- 创建 Feature PR

**数据流位置：** `外部API → [EXCH] → stocks.get_data() → PLAT/STRAT`

---

### PLAT — 平台/引擎开发

**身份背景：** 系统工程师，精通回测系统架构。作为中间调度层，连接交易所和策略。

**核心职责：**
- 编排完整的模拟交易流程：获取行情(EXCH) → 调用策略(STRAT) → 执行交易(EXCH)
- 维护引擎调度层（`simulator_engine.py`、`simulator.py`、`clock.py`）
- 维护 `stocks.py` 框架（策略注册表架构、回测请求模型）
- 创建 Feature PR

**分包角色：**
```
EXCH → 提供"交易能力"（怎么买、怎么查价格）
STRAT → 提供"策略逻辑"（什么时候该买卖）
PLAT → 中间调度（怎么组织流程、怎么跑回测）
```

---

## 三、文件所有权矩阵

每个文件的 **Owner** 对其有修改批准权/维护主力权，**Cross** 表示该角色可能因接口依赖需要同步修改。  
**空白的 Cross** = 不可擅自修改，必须先与 Owner 协商。

### 2.1 顶层文件

| 文件 | Owner | Cross | 说明 |
|------|-------|-------|------|
| `main.py` | WEB | PLAT | Web 入口，调试模式配置 |
| `stocks.py` | PLAT | STRAT | 业务入口 + 策略注册表。STRAT 新增策略可追加注册项，但平台架构不改 |
| `requirements.txt` | PLAT | — | 依赖管理 |
| `pip.conf` | PLAT | — | pip 配置 |
| `.flake8` / `.pylintrc` / `mypy.ini` | LEAD | — | 代码规范配置 |

### 2.2 `source/` — 数据源层（Owner: **EXCH**）

```
source/
├── base_provider.py          # EXCH — 数据源接口 ABC
├── data_provider.py          # EXCH — 聚合调度、缓存逻辑
├── provider_utils.py         # EXCH — 共享工具函数
├── akshare_provider.py       # EXCH — AKShare 实现
├── baostock_provider.py      # EXCH — Baostock 实现
├── tencent_provider.py       # EXCH — 腾讯数据源
├── sina_provider.py          # EXCH — 新浪数据源
├── sohu_provider.py          # EXCH — 搜狐数据源
├── eastmoney_provider.py     # EXCH — 东方财富数据源
├── cailianpress_provider.py  # EXCH — 财联社数据源
├── stooq_provider.py         # EXCH — Stooq 数据源
└── README.md
```

> **边界：** 任何人不得在 source/ 下新增非 Provider 文件。新增数据源必须继承 `BaseProvider`。**STOCKS 团队不得绕过 Provider 层直接调用外部 API。**

### 2.3 `simulator/` — 模拟交易引擎（EXCH + PLAT 分治）

```
simulator/
├── exchange_interface.py     # EXCH — 交易所接口抽象（StockExchange）
├── base_engine.py            # EXCH — 账户模型（Position/Account/TradeOrder/TradeResult）
├── simulated_exchange.py     # EXCH — 仿真交易所基础实现
├── backtest/
│   ├── exchange.py           # EXCH — 回测交易所
│   └── clock.py              # PLAT — 回测时钟
├── live/
│   ├── exchange.py           # EXCH — 实盘交易所（预留）
│   └── __init__.py
├── realtime/
│   ├── exchange.py           # EXCH — 实时仿真交易所
│   └── __init__.py
├── real_engine.py            # PLAT — 实盘引擎
├── simulator_engine.py       # PLAT — 具体引擎实现
├── simulator.py              # PLAT — 引擎入口调度
└── README.md
```

> **分治原则：** EXCH 负责"交易能力"（怎么连接、怎么买卖、怎么查行情）。PLAT 负责"调度编排"（什么时候买卖、怎么组织回测流程）。两者通过 `StockExchange` 接口协作。
>
> **注意：** `real_engine.py` 归 PLAT（引擎编排），`live/exchange.py` 归 EXCH（券商接口）。区分标准：涉及交易系统连接的归 EXCH，涉及策略调度的归 PLAT。

### 2.4 `solver/` — 策略算法（Owner: **STRAT**）

```
solver/
├── sma_strategy.py           # STRAT — SMA 策略
├── dual_ma_strategy.py       # STRAT — 双均线策略
├── bollinger_strategy.py     # STRAT — 布林带策略
├── rsi_strategy.py           # STRAT — RSI 策略
├── mean_cost_strategy.py     # STRAT — 均值成本策略
├── fixed_amount_strategy.py  # STRAT — 定投策略
├── futures_open_hour_strategy.py  # STRAT — 期货开盘策略
├── signal_template_strategy.py    # STRAT — 信号模板策略
└── README.md
```

> **STRAT 专属区域：** 只改 solver/。  
> **接口契约：** 新增策略必须注册到 `stocks.py` 的策略注册表（追加 `AUTO_STRATEGY_SPEC`）。注册表架构本身由 PLAT 维护，STRAT 只追加条目。  
> **命名规范：** 新增策略文件 `snake_case.py`，策略类名 `PascalCaseStrategy`。

### 2.5 `gui/` — Web 界面（Owner: **WEB**）

```
gui/
├── web.py                    # WEB — Flask 路由 + API 处理函数
│                              #   路由范围：20+ 路由（首页、策略配置、回测执行、结果展示）
│                              #   涉及 API 响应格式，与 PLAT 通过 stocks.py 交互
├── backtest_progress.py      # WEB — SSE 进度推送
├── templates/
│   ├── index.html            # WEB — 首页
│   ├── select_stock.html     # WEB — 选股
│   ├── select_strategy.html  # WEB — 选策略
│   ├── select_mode.html      # WEB — 选模式
│   ├── select_time_range.html# WEB — 选时间
│   ├── strategy_sma.html     # WEB — SMA 参数页
│   ├── strategy_mean_cost.html# WEB — 均值成本参数页
│   ├── strategy_fixed_amount.html  # WEB — 定投参数页
│   ├── strategy_signal_template.html  # WEB — 信号模板参数页
│   ├── strategy_dynamic.html  # WEB — 动态策略参数页
│   ├── result.html           # WEB — 结果页
│   ├── result_mean.html      # WEB — 均值成本结果页
│   ├── backtest_progress.html# WEB — 进度展示页
│   └── strategy_dynamic.html # WEB — 通用策略参数页
├── static/                   # WEB — CSS/JS/图片（用户可自己替换）
├── stock_list.json           # WEB — 股票列表缓存
└── README.md
```

> **WEB ↔ PLAT 接口边界：**  
> `gui/web.py` 调用 `stocks.get_data()`、`stocks.run_backtest()` 等接口获取数据。  
> `gui/web.py` 不应直接调用 `source/` 或 `simulator/`。  
> 新增 API 路由，如果只是为了前端展示，WEB 自己加。如果涉及新的后端能力，需 PLAT 配合。
>
> **例外：** 进度推送（`backtest_progress.py`）是 WEB 和 PLAT 共用的（PLAT 的 `run_backtest` 写进度，WEB 的 SSE 读进度）。修改需双方协商。

### 2.6 业务入口 `stocks.py`（Owner: **PLAT**, Cross: **STRAT**, Cross: **EXCH**）

```
stocks.py — 按职责划分：
┌─ PLAT 专属（引擎调度）─────────────────────┐
│  run_backtest()            执行回测        │
│  create_backtest_request() 创建回测请求    │
│  _build_strategy_registry() 注册表架构    │
│  list_strategy_specs()     列出策略        │
│  get_strategy_spec()       获取策略        │
│  StrategyParameter         参数定义类      │
│  StrategySpec              策略规格类      │
│  BacktestRequest           回测请求类      │
└──────────────────────────────────────────┘
┌─ PLAT 主责 + EXCH 配合（数据获取）─────────┐
│  get_data()                数据获取        │
│  init()                    系统初始化      │
└──────────────────────────────────────────┘
┌─ STRAT 可追加（策略 run 函数）─────────────┐
│  AUTO_STRATEGY_SPEC (在 solver/*.py 中)  │
│  run_sma_backtest()         各策略run函数  │
│  run_mean_cost()                          │
│  run_fixed_amount()                      │
│  run_module_strategy_backtest()          │
│  run_signal_template()                   │
└──────────────────────────────────────────┘
```

> **数据流：** `EXCH` 提供 `source/data_provider.get_data()` 底层实现。`stocks.get_data()` **代理调用** EXCH 的能力。PLAT 的引擎通过 `stocks.get_data()` 获取行情数据，通过 `StockExchange` 接口执行交易。  
>
> **STRAT 新增策略：** 在 `solver/` 下创建新策略文件 + `AUTO_STRATEGY_SPEC`，自动发现，不需改 `stocks.py`。

### 2.7 `tests/` — 测试（ITEST / GTEST）

```
tests/
├── guitests/                              ← Owner: GTEST
│   ├── test_gui_app.py           GTEST — 基本 GUI 功能
│   ├── test_gui_all_strategies_e2e.py  GTEST — 全策略端到端
│   ├── test_gui_backtest_report_e2e.py GTEST — 回测报告
│   ├── test_realtime_lot_calculation.py  GTEST — 实时计算
│   └── README.py
│
├── test_stocks.py              ITEST — 业务入口测试
├── test_simulator.py           ITEST — 模拟器测试
├── test_simulator_engine.py    ITEST — 引擎测试
├── test_integration.py         ITEST — 集成测试
├── test_main.py                ITEST — 入口测试
├── test_main_run.py            ITEST — 运行测试
├── test_fixed_amount_strategy.py  ITEST — 策略测试
├── test_low_frequency_strategies.py ITEST — 低频策略测试
├── test_futures_open_hour_strategy.py ITEST — 期货策略测试
├── test_run_sma.py             ITEST — SMA 回测测试
├── test_data_provider_cache.py ITEST — 数据缓存测试
├── test_data_provider_stooq.py ITEST — 数据源测试
├── test_cache_utils.py         ITEST — 缓存工具测试
├── test_akshare_provider_compat.py ITEST — 数据源兼容
├── test_backtest_progress.py   ITEST — 进度条测试
├── test_futures_missing_data.py ITEST — 缺失数据处理
├── test_adjustment.py          ITEST — 复权测试
├── test_dividend_adjustment.py ITEST — 分红复权测试
├── test_yangtze_power.py       ITEST — 特定股票测试
├── test_test_utils.py          ITEST — 测试工具
├── test_utils.py               ITEST — 工具函数测试
├── test_gui_download_policy.py ITEST — 下载策略测试
├── test_guitest_workflow_report.py ITEST — GUI 测试报告
├── test_comment_guitest_report_script.js  — JS 辅助脚本
├── __init__.py
└── README.md
```

> **写测试原则：**
> - ITEST 的测试落在 `tests/test_*.py`，测试 PLAT / STRAT 的代码
> - GTEST 的测试落在 `tests/guitests/`，测试 WEB 的界面
> - 当测试发现 bug，ITEST/GTEST 在 PR 评论中 @对应角色（PLAT/STRAT/WEB）
> - 新增功能必须有对应的新增测试

### 2.8 `.github/workflows/` — CI/CD（按角色归属）

| 文件 | Owner | 说明 |
|------|-------|------|
| `test.yml` | ITEST | 单元测试 + 集成测试 |
| `testgui.yml` | GTEST | 端到端 GUI 测试（Playwright） |
| `lint.yml` | LEAD | 代码风格检查（flake8 + mypy） |
| `package.yml` | PLAT | 打包发布 |
| `opencode.yml` | HERMES | （备用/仅测试用） |

### 2.9 其他文件

| 文件 | Owner | 说明 |
|------|-------|------|
| `AGENTS.md` | HERMES | 本文件，团队协作规范 |
| `CLAUDE.md` | ARCH | 项目约定，ARCH 更新 |
| `data/` | PLAT | 数据缓存目录，程序自动生成 |
| `docs/` | 相关角色 | 文档，谁写的谁维护 |
| `tools/` | PLAT | 辅助工具 |
| `test_ak.py` / `probe_stocks.py` / `probe_output.txt` | — | 调试遗留文件，可清理 |
| `.github/copilot-instructions.md` | — | Copilot 配置 |
| `.github/agents/` / `.github/instructions/` | — | 第三方工具配置 |
| `.github/scripts/` | GTEST | GUI 测试脚本 |
| `.github/skills/` | — | 第三方 skill 定义 |

---

## 三、角色协作边界—谁不能碰什么

| 角色 | 绝不能碰 | 跨模块必须先沟通 |
|------|---------|----------------|
| **WEB** | `source/` `simulator/` `solver/` `stocks.py`（框架部分） | 新增 API 路由时对接 PLAT |
| **EXCH** | `gui/` `solver/` `simulator/`（PLAT 管辖的引擎文件） | 改 `get_data()` 签名时对接 PLAT |
| **PLAT** | `gui/templates/` `source/`（EXCH 的数据源） `solver/` | 改回测流程时对接 EXCH / STRAT |
| **STRAT** | `source/` `simulator/` `gui/` | 新增策略通过 `AUTO_STRATEGY_SPEC` 自动注册 |
| **ITEST** | `solver/` 的策略逻辑、`gui/templates/` | 发现 bug 时 @ 对应角色 |
| **GTEST** | `source/` `simulator/` `solver/` | 发现 bug 时 @ 对应角色 |
| **ARCH** | 不写执行代码（只做设计 + Issue） | 设计评审后交给对应角色 |
| **LEAD** | 只 Review 不写代码 | 仲裁时 @ 对应角色 |
| **QA** | 只验收不修改 | 不通过时 label:待修复 |

---

## 四、协作流程

```
[PM] 发现需求 → 建 Issue + label:需求
  │
  ▼ Hermes 检测到 label:需求
[ARCH(Pro)] 读取 Issue → 分析设计 → 拆任务 → 建 sub-issue
  │ 每个 sub-issue 标注所属角色 + label:任务
  │ 如有必要 → 建 Design PR 描述接口设计
  ▼
[Hermes 按 sub-issue label 触发]
  ┌──────┬──────┬──────┬──────┬──────┐
  ▼      ▼      ▼      ▼      ▼      ▼
 WEB   EXCH   PLAT   STRAT  ITEST GTEST
(UI)  (数据/ (引擎/  (策略)  (集成  (GUI
       行情)  调度)          测试)  测试)
  │      │      │      │      │      │
  └──────┴──┬───┘      │      │      │
            │         Feature PR
            │          │
            └─────┬────┘
                  ▼
         [LEAD(Pro)] Review PR
           ├── CI 通过 + Code OK → label:待验收
           └── 不通过 → PR 评论 @角色 + label:待修复
                          │
                          ▼ 修复后循环
                   [QA] 验收测试
                     ├── 通过 → 合并 PR
                     └── 不通过 → label:待修复
```

---

## 五、代码规范

### 命名
- 模块名：`snake_case.py`
- 类名：`PascalCase`
- 函数/变量：`snake_case`
- 私有方法/属性：`_leading_underscore`

### 类型注解
所有函数参数和返回值必须有类型注解（mypy 严格模式）。

### 异常处理
- 不吞异常（不写裸 `except: pass`）
- 自定义异常继承 `Exception`
- 外部调用失败要有 fallback 或明确报错

### 测试规范
- 单测/集成测试：`tests/test_*.py`（ITEST）
- GUI 测试：`tests/guitests/`（GTEST）
- PR 中新增功能必须有新增测试

---

## 六、策略接口规范

所有策略文件（`solver/*.py`）必须遵循以下隐式接口，以支持自动发现注册：

```python
# 在策略模块中声明
AUTO_STRATEGY_SPEC = {
    "key": "策略唯一标识",
    "name": "策略展示名称",
    "category": "策略分类",
    "parameters": [
        {"name": "param1", "label": "参数1", "type": "float", "default": 20},
    ],
}

# 策略类必须提供
class StrategySimulator:
    def prepare_backtest_data(self, df, **params) -> pd.DataFrame:
        """计算技术指标，返回增强后的 DataFrame"""
        ...

    def simulate(self, df, **params) -> dict:
        """执行回测逻辑，返回结果 dict"""
        ...

    def get_parameters(self) -> list:
        """返回参数配置列表"""
        ...
```

新增策略：
1. 在 `solver/` 下创建 `xxx_strategy.py`
2. 声明 `AUTO_STRATEGY_SPEC`
3. 实现策略类
4. 不需要改任何其他文件

---

本文件由 Hermes Agent 维护，随团队协作流程迭代更新。
最后更新：2026-06-15
