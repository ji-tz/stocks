# AGENTS — Stocks 量化回测系统团队手册

本文件定义了 Stocks 项目的 AI 团队架构、角色职责、**严格文件所有权**与协作流程。  
每个子 Agent 在执行任务前必须读取本文件，明确自己的权责范围。

---

## 一、团队角色总览

| | 角色 | 代号 | 模型 | 核心职责 |
|---|------|------|------|---------|
| 1 | 产品经理 | PM | 普通 | 熟悉软件，发现痛点和需求，对标竞品提 Issue |
| 2 | 架构师 | ARCH | **Pro** | 拆解需求、设计模块、定接口、开 sub-issue |
| 3 | Web 前端 | WEB | 普通 | UI/UX 设计、Flask 模板、前端交互逻辑 |
| 4 | **交易所** | **EXCH** | 普通 | 行情数据获取 + 账户持仓管理 + 交易执行 |
| 5 | **交易员** | **TRADER** | 普通 | 控制时间流程、驱动回测、执行买卖操作 |
| 6 | **策略算法** | **STRAT** | 普通 | 撰写策略逻辑、输出买卖信号（不直接操作） |
| 7 | 集成测试 | ITEST | 普通 | 接口/集成测试、边界测试、维护 test.yml |
| 8 | GUI 测试 | GTEST | 普通 | Playwright 端到端测试、维护 testgui.yml |
| 9 | 研发主管 | LEAD | **Pro** | Review PR、运行测试、仲裁修复责任 |
| 10 | 验收测试 | QA | — | 自动化端到端验收，通过后合并 PR |

---

## 二、核心概念 — 三层协作模型

```
STRAT（策略算法）
  │ 输出买卖信号（buy/sell/hold）
  ▼
TRADER（交易员）
  │ 推进时间（一天、一小时…），问策略"现在该不该操作"，然后执行
  ▼
EXCH（交易所）
  │ 提供行情数据 + 执行买卖 + 记录持仓和资金
```

**三方各司其职：**

```
EXCH  → "市场"——提供数据、执行交易、管账本
TRADER → "操盘手"——推进时间、读策略信号、操作买卖
STRAT → "军师"——只出主意（写策略公式），不碰钱
```

---

## 三、角色详细定义

### EXCH — 交易所

**身份背景：** 证券交易所系统工程师。精通 A 股行情数据接口、撮合机制、账户资金管理。  
交易所是数据提供方 + 交易执行方 + 账户记账方的三位一体。

**核心职责：**
- 维护行情数据源（`exchange/source/` 所有 Provider）— 获取股票价格
- 维护交易执行接口（`StockExchange`）— 提供 `buy()/sell()` 能力
- 维护账户模型（Position、Account、资金计算）— 记录持仓、盈亏
- 维护 `exchange/` 目录下所有交易所实现（基类、回测、实盘、实时仿真）
- 不关心"什么时候买卖"——那是交易员的事

**接口：**
- `get_data(symbol, start, end)` → DataFrame — 给 TRADER 和 STRAT 用
- `StockExchange.buy(date, price, shares)` → TradeResult
- `StockExchange.sell(date, price, shares)` → TradeResult
- `Account.get_position()` → 当前持仓
- `Account.get_total_value(price)` → 总资产估值

---

### TRADER — 交易员

**身份背景：** 资深量化交易员，熟悉回测流程、交易节奏控制。  
交易员是**时间驱动者**——推进时间轴，在每个时间节点上问策略"该不该动"，然后操作。

**核心职责：**
- 控制模拟交易的时间进程（按天/小时 tick 推进）
- 在每个时间 tick：
  1. 从 **EXCH** 获取当前行情
  2. 调用 **STRAT** 的策略信号（`prepare_backtest_data` → `simulate`）
  3. 根据信号通过 **EXCH** 执行 `buy()/sell()`
  4. 记录交易结果
- 驱动完整的回测流程（`run_backtest()`）
- 维护 `trader/` 目录下所有交易逻辑（模拟器、引擎、时钟）

**工作流：**
```
for each day in 回测时间范围:
    行情 = EXCH.get_data(当天)
    信号 = STRAT.decide(行情, 当前持仓)
    if 信号 == 'buy':
        EXCH.buy(当天, 开盘价, 数量)
    elif 信号 == 'sell':
        EXCH.sell(当天, 开盘价, 数量)
    记录当天持仓和盈亏
```

---

### STRAT — 策略算法

**身份背景：** 量化研究员，数学/统计背景。  
**策略只负责写公式、算信号，不碰交易。**

**核心职责：**
- 撰写策略逻辑（技术指标计算、信号生成）
- 输出 `buy`/`sell`/`None` 信号——由交易员去执行
- 维护已有策略，新增策略通过 `strategy/` 目录扩展
- 为策略编写单测（可以自行向 tests/ 提交，但文件归 ITEST 维护）

**策略接口：**
```python
class Strategy:
    @staticmethod
    def prepare_backtest_data(df: pd.DataFrame, **params) -> pd.DataFrame:
        """计算技术指标，返回增强后的 DataFrame"""

    @staticmethod
    def simulate(df: pd.DataFrame, position, **params) -> dict:
        """根据行情和持仓输出信号，返回 {'signal': 'buy'|'sell'|None, ...}"""

    @staticmethod
    def get_parameters() -> list:
        """返回参数配置列表（用于 GUI 表单）"""
```

> **STRAT 不直接调用 `buy()/sell()`**。STRAT 只返回信号，由 TRADER 执行。  
> STRAT 需要行情数据时，通过 EXCH 的 `get_data()` 获取。

---

## 四、严格文件所有权

**规则：每个文件只有一个 Owner。** 其他角色如需修改，先提 Issue 或 PR @Owner 协商。

### 4.1 顶层文件

| 文件 | Owner | 说明 |
|------|-------|------|
| `main.py` | WEB | Web 入口 |
| `requirements.txt` | TRADER | 依赖管理 |
| `pip.conf` | TRADER | pip 配置 |
| `.flake8` / `.pylintrc` / `mypy.ini` | LEAD | 代码规范配置 |

### 4.2 `exchange/` — 全部归 **EXCH**

交易所目录，包含行情数据源 + 交易执行 + 账户管理。

```
exchange/
├── __init__.py                    EXCH
├── README.md                      EXCH
├── base_engine.py                 EXCH
├── exchange_interface.py          EXCH
├── simulated_exchange.py          EXCH
├── real_engine.py                 EXCH
├── source/                        EXCH（所有数据 Provider）
│   ├── base_provider.py           EXCH
│   ├── data_provider.py           EXCH
│   ├── provider_utils.py          EXCH
│   ├── akshare_provider.py        EXCH
│   ├── baostock_provider.py       EXCH
│   ├── tencent_provider.py        EXCH
│   ├── sina_provider.py           EXCH
│   ├── sohu_provider.py           EXCH
│   ├── eastmoney_provider.py      EXCH
│   ├── cailianpress_provider.py   EXCH
│   ├── stooq_provider.py          EXCH
│   └── README.md                  EXCH
├── backtest/
│   ├── __init__.py                EXCH
│   └── exchange.py                EXCH
├── live/
│   ├── __init__.py                EXCH
│   └── exchange.py                EXCH
└── realtime/
    ├── __init__.py                EXCH
    └── exchange.py                EXCH
```

### 4.3 `trader/` — 全部归 **TRADER**

交易员目录，包含时间推进、回测调度、交易信号执行。

```
trader/
├── simulator.py                   TRADER
├── simulator_engine.py            TRADER
├── clock.py                       TRADER
├── stocks.py                      TRADER（业务入口，三层协作调度中心）
└── __init__.py                    TRADER
```

> `stocks.py` 是三层协作的调度入口。STRAT/EXCH 如需修改 → 提 PR @TRADER Review。

### 4.4 `strategy/` — 全部归 **STRAT**

```
strategy/
├── sma_strategy.py                STRAT
├── dual_ma_strategy.py            STRAT
├── bollinger_strategy.py          STRAT
├── rsi_strategy.py                STRAT
├── mean_cost_strategy.py          STRAT
├── fixed_amount_strategy.py       STRAT
├── futures_open_hour_strategy.py  STRAT
├── signal_template_strategy.py    STRAT
└── README.md                      STRAT
```

### 4.6 `gui/` — 全部归 **WEB**

```
gui/
├── web.py                      WEB
├── backtest_progress.py        WEB
├── templates/ (13个HTML文件)     WEB
├── static/                     WEB
├── stock_list.json             WEB
└── README.md                   WEB
```

> `backtest_progress.py` 虽然是 SSE 端点和 TRADER 的运行进度有关，但代码本身是 WEB 的文件。TRADER 如需改动 SSE 格式 → 提 PR。

### 4.7 `tests/` — 严格单 Owner，按层分子目录

测试目录按类型分为三个子目录：

```
tests/
├── unit/                  ← 单元测试（纯逻辑，不依赖真实API/数据）
│   ├── test_stocks.py            ITEST （测试 TRADER 的 stocks.py）
│   ├── test_simulator.py         ITEST （测试 TRADER 的 simulator）
│   ├── test_simulator_engine.py  ITEST （测试 TRADER 的引擎）
│   ├── test_main.py              ITEST （入口测试）
│   ├── test_main_run.py          ITEST （运行测试）
│   ├── test_fixed_amount_strategy.py ITEST （测试 STRAT）
│   ├── test_low_frequency_strategies.py ITEST （测试 STRAT）
│   ├── test_futures_open_hour_strategy.py ITEST （测试 STRAT）
│   ├── test_run_sma.py           ITEST （测试 STRAT）
│   ├── test_data_provider_cache.py ITEST （测试 EXCH）
│   ├── test_data_provider_stooq.py ITEST （测试 EXCH）
│   ├── test_cache_utils.py       ITEST （测试 EXCH）
│   ├── test_akshare_provider_compat.py ITEST （测试 EXCH）
│   ├── test_backtest_progress.py ITEST （测试进度条）
│   ├── test_futures_missing_data.py ITEST （测试数据）
│   ├── test_adjustment.py        ITEST （测试复权）
│   ├── test_dividend_adjustment.py ITEST （测试分红）
│   ├── test_gui_download_policy.py ITEST （GUI 下载测试）
│   ├── test_guitest_workflow_report.py ITEST （测试报告）
│   ├── test_test_utils.py        ITEST （测试工具）
│   └── test_utils.py             ITEST （工具函数测试）
├── integration/           ← 集成测试（依赖真实API/数据库/外部服务）
│   ├── test_integration.py       ITEST （整体集成测试）
│   └── test_yangtze_power.py     ITEST （真实股票数据验证）
├── guitests/               ← GUI 端到端测试（归 GTEST）
│   ├── test_gui_app.py           GTEST
│   ├── test_gui_backtest_report_e2e.py GTEST
│   ├── test_gui_all_strategies_e2e.py GTEST
│   ├── test_realtime_lot_calculation.py GTEST
│   └── ...
├── __init__.py             ITEST
└── README.md               ITEST
```

| 目录 | Owner | 说明 |
|------|-------|------|
| `tests/unit/` 全部 | **ITEST** | 纯逻辑单元测试，不调用真实API |
| `tests/integration/` 全部 | **ITEST** | 集成测试，依赖真实数据源 |
| `tests/guitests/` 全部 | **GTEST** | GUI 端到端测试 |

> **说明：** 虽然测试文件测试的是 EXCH/STRAT/TRADER 的代码，但**测试文件本身的维护责任归 ITEST**。发现被测代码的 bug → ITEST 在 PR 上 @ 对应角色修复。

### 4.8 `.github/workflows/` — CI/CD

| 文件 | Owner | 说明 |
|------|-------|------|
| `test.yml` | ITEST | 单元测试 + 集成测试 |
| `testgui.yml` | GTEST | 端到端 GUI 测试 |
| `lint.yml` | LEAD | 代码风格检查 |
| `package.yml` | TRADER | 打包发布 |
| `opencode.yml` | HERMES | （备用） |

### 4.9 其他

| 文件 | Owner | 说明 |
|------|-------|------|
| `AGENTS.md` | HERMES | 本文件 |
| `CLAUDE.md` | ARCH | 项目约定 |
| `data/` | EXCH | 数据缓存（程序自动生成） |
| `docs/` | 相关角色 | 谁写的谁维护 |
| `tools/` | TRADER | 辅助工具 |
| `simulator/` | — | 已清理。交易所代码 → `exchange/`，交易员代码 → `trader/` |
| `source/` | — | 已清理。数据 Provider → `exchange/source/` |
| `solver/` | — | 已清理。策略代码 → `strategy/` |
| `test_ak.py` / `probe_*.py` | — | 调试遗留文件，可清理 |
| `.github/`（非 workflow） | — | 第三方工具配置，无需维护 |

---

## 五、角色协作边界

### 严格规则
- **每个文件只有一个 Owner。** 修改前先看文件归属。
- **不跨 Owner 直接提交代码。** 需要改其他角色的文件 → 先提 Issue 或 PR @Owner。

### 谁不能碰什么

| 角色 | 绝不能碰的目录 |
|------|---------------|
| **WEB** | `exchange/` `strategy/` `trader/` |
| **EXCH** | `gui/` `strategy/` `trader/` |
| **TRADER** | `gui/` `exchange/source/` `strategy/` |
| **STRAT** | `exchange/` `trader/` `gui/` |
| **ITEST** | 不直接修改业务代码（发现 bug 时 @ 对应角色） |
| **GTEST** | 不直接修改业务代码（发现 bug 时 @ 对应角色） |
| **ARCH** | 不写执行代码（只做设计 + Issue） |
| **LEAD** | 不写执行代码（只 Review） |
| **QA** | 只验收不修改 |

---

## 六、协作流程（完整工作流）

### 6.1 标签体系

| 标签 | 用途 | 谁打 |
|------|------|------|
| `requirements` | 新需求/功能请求 | PM / 用户 / 任何人 |
| `exchange` | 交易所层任务 | ARCH |
| `trader` | 交易员层任务 | ARCH |
| `strategy` | 策略算法层任务 | ARCH |
| `gui` | Web 前端任务 | ARCH |
| `test` | 测试相关任务 | ARCH |
| `ci` | CI/CD 配置任务 | ARCH |
| `bug` | 缺陷报告 | 任何人 |
| `needs-triage` | 待架构师拆解 | 提 Issue 时自动打 |
| `triaged` | 已拆解完成 | ARCH |
| `ai-in-progress` | AI 正在处理中 | Hermes 自动 |
| `needs-review` | 待 LEAD Review | 开发完成时自动 |
| `needs-qa` | 待 QA 测试 | LEAD |
| `ai-done` | AI 已完成 | QA |
| `ai-routed` | 已进入流程 | Hermes 自动 |

### 6.2 完整工作流步骤

核心原则：**Issue 管需求跟踪，PR 管代码实现。**

```
┌─────────────────────────────────────────────────────┐
│  第一步：提 Issue                                    │
│  PM / 用户 / ARCH / LEAD / QA 任何人                  │
│  打标签：requirements / bug / exchange / trader 等    │
│  自动补打：needs-triage                               │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│  第二步：ARCH 拆解 + 建 PR（Pro 模型）                 │
│                                                      │
│  1. 读取 Issue → 分析需求 → 判断范围                  │
│  小 Issue → 直接指定一个 Agent                        │
│  大 Issue → 拆成多个子任务，每个标注角色标签            │
│                                                      │
│  2. 在 Issue 评论中发布拆解方案：                       │
│     ## ARCH 拆解方案                                   │
│     ### 任务1：[角色] - [描述]                        │
│     ### 任务2：[角色] - [描述]                        │
│     执行顺序：[R1] → [R2] → [R3]                     │
│                                                      │
│  3. ⭐ 创建 PR（从 main 开分支）。分支名：              │
│     feat/issue-<num>-<short-desc>                    │
│     PR 标题关联 Issue #<num>                          │
│     PR body 贴拆解方案 + 各子任务 checkboxes           │
│                                                      │
│  4. 打标签：triaged                                   │
│  移除标签：needs-triage                                │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│  第三步：AGENT 串行开发（本地 OpenCode）               │
│                                                      │
│  ⚠️ 串行执行，一次只开发一个 Agent 的任务              │
│  顺序由 ARCH 指定（在 Issue 评论中标注）               │
│                                                      │
│  1. Hermes 检测到带角色标签且无 ai-in-progress 的子任务 │
│  2. checkout 已有 PR 分支（← 同一个分支！）             │
│     git checkout feat/issue-<num>-<slug>               │
│  3. 运行 OpenCode 或直接实现                          │
│  4. commit + push 到 PR 分支 → 自动触发 CI           │
│  5. 在 Issue 评论中标明该子任务已完成 + 修改要点        │
│  6. 在 PR 的 checkbox 中勾掉已完成项                   │
│  7. 移除当前角色的标签 + ai-in-progress                 │
│  8. 取下个子任务（下个 cron tick 自动处理）             │
│                                                      │
│  角色分工（严格文件所有权）：                           │
│  · STRAT → strategy/                                 │
│  · EXCH  → exchange/                                 │
│  · TRADER→ trader/                                   │
│  · WEB   → gui/                                      │
│  · ITEST → tests/unit/ + tests/integration/          │
│  · GTEST → tests/guitests/                            │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│  第四步：CI Workflow + LEAD Review                    │
│                                                      │
│  每个 push 到 PR 分支自动触发 CI：                     │
│  · Test  ✅/❌   单元 + 集成测试                      │
│  · Lint  ✅/❌   代码风格                             │
│  · Test GUI ✅/❌  GUI 端到端测试                      │
│  · Package ✅/❌  打包                                │
│                                                      │
│  所有子任务完成后 + CI 通过 → LEAD Review             │
│  · 代码 OK → 打 needs-qa                             │
│  · 有问题 → 评论 @对应 Agent 修复                     │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│  第五步：QA 本地测试                                   │
│                                                      │
│  QA checkout PR 分支 → 本地验证                      │
│  · 功能验证 + 回归验证 + 边界情况                      │
│                                                      │
│  通过 → 打 ai-done（允许合并）                        │
│  不通过 → 评论 @对应 Agent 修复                       │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│  第六步：合并 PR（CI 必须通过）                         │
│                                                      │
│  QA 确认 ai-done → 合并 PR 到 main                   │
│  关闭关联 Issue                                       │
└─────────────────────────────────────────────────────┘
```

### 6.3 标签流转规则

```
提 Issue → [needs-triage] → ARCH 拆解 + 建 PR → [triaged]
                                    → 子任务打角色标签
                                                ↓
                        Hermes 检测 → 串行 push 到同一 PR 分支
                                                ↓
                        每个角色完成 → 更新 Issue 评论 + 勾 PR checkbox
                                                ↓
                        最后一个子任务完成 → [needs-review]
                                                ↓
                        LEAD Review:
                          ├── CI 全过 + 代码 OK → [needs-qa] → QA 测试
                          │                                    ↓
                          │                           QA 通过 → [ai-done] → 合并 PR
                          │                                    ↓          ↓
                          │                           QA 不通过 → @Agent 修复  关闭 Issue
                          │
                          └── CI 失败 / 代码问题 → @Agent 修复
```

### 6.4 串行执行规则

- **一次只开发一个 Agent 的任务**，避免多人改同一文件的冲突
- ARCH 在拆解时确定执行顺序（通常：STRAT → EXCH → TRADER → WEB → 测试）
- Hermes 自动检测当前轮到谁，等上一个 push 后再启动下一个

---

## 七、代码规范

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
- 单测/集成测试：`tests/test_*.py`（ITEST 维护）
- GUI 测试：`tests/guitests/`（GTEST 维护）
- PR 中新增功能必须有对应新增测试

---

## 八、策略接口规范

所有策略文件（`strategy/*.py`）必须遵循以下隐式接口：

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

# 策略类 — 只输出信号，不执行交易
class StrategySimulator:
    def prepare_backtest_data(self, df, **params) -> pd.DataFrame:
        """计算技术指标，返回增强后的 DataFrame"""

    def simulate(self, df, **params) -> dict:
        """输出信号 {'signal': 'buy'|'sell'|None, ...}，由 TRADER 执行"""

    def get_parameters(self) -> list:
        """返回参数配置列表"""
```

新增策略：
1. 在 `strategy/` 下创建 `xxx_strategy.py`
2. 声明 `AUTO_STRATEGY_SPEC`
3. 实现策略类（只返回信号）
4. 不需要改任何其他文件

---

---

本文件由 Hermes Agent 维护，随团队协作流程迭代更新。
最后更新：2026-06-16（v3 — 工作流迁移到独立的 WORKFLOW.md）

> 开发工作流（Issue → ARCH → 角色实现 → LEAD → QA → 合并）请参见 **[WORKFLOW.md](./WORKFLOW.md)**。

