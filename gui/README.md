# GUI 模块 - Web 界面

## 概述

本模块提供基于 Flask 的 Web 界面，用于可视化配置和运行量化投资策略回测。

## 功能特点

- 🎨 友好的用户界面，无需编写代码即可运行回测
- 📊 策略选择页面支持自动注册策略（包含内置策略与新增策略）
- 🔧 内置策略保留专门配置页面，自动注册策略使用通用参数配置页面
- 🧩 新增信号模板策略页面，支持按模板直接配置买卖触发条件与执行方式
- 🗂️ 首页展示最近使用股票与全部本地缓存股票
- 📈 统一的回测结果展示，包含交易明细和历史记录
- ✅ 客户端日期格式校验，提升用户体验

## 目录结构

```
gui/
├── README.md           # 本文档
├── web.py             # Flask 应用主文件
├── templates/         # HTML 模板目录
│   ├── index.html                    # 首页（策略选择）
│   ├── strategy_sma.html             # SMA 策略配置页面
│   ├── strategy_mean_cost.html       # 均值成本策略配置页面
│   ├── strategy_fixed_amount.html    # 定投策略配置页面
│   ├── result.html                   # 简单结果展示页面
│   └── result_mean.html              # 详细结果展示页面
└── static/            # 静态资源目录（CSS、JS、图片等）
```

## 启动 Web 服务

### 方法 1：直接运行（开发模式）

```bash
python -m gui.web
```

服务将在 `http://127.0.0.1:5000` 启动，debug 模式默认开启。

### 方法 2：使用 Flask 命令行

```bash
flask --app gui.web run
```

### 方法 3：生产环境部署

在生产环境中，建议使用 WSGI 服务器（如 Gunicorn）：

```bash
pip install gunicorn
# 设置安全的secret_key环境变量
export SECRET_KEY="your-random-secret-key-here"
gunicorn -w 4 -b 0.0.0.0:5000 gui.web:app
```

**生产环境安全配置：**
- 务必设置 `SECRET_KEY` 环境变量，使用强随机密钥
- 可使用 `python -c "import secrets; print(secrets.token_hex(32))"` 生成密钥
- 不要在生产环境使用默认的 secret_key

## 用户操作流程

新的用户操作流程分为六个步骤：

1. **选取股票**：在首页通过股票代码或名称搜索股票（支持精确搜索）
2. **选取策略**：从策略注册表中选择策略（自动包含新增策略）
3. **选择运行模式**：选择回测仿真、实时仿真或实盘交易
4. **设置回测时间段**（新增）：使用日期选择器设置回测的起始和结束日期，支持快捷时间段选择
5. **配置策略参数**：设置策略参数、初始资金等（时间段设置已移至上一步）
6. **查看复盘结果**：查看回测结果，包括收益、交易明细等

## 页面说明

### 1. 股票选择页面 (`/`) - 首页

用户旅程的第一步，选择要回测的股票。

**功能特点：**
- 🔍 **搜索功能**：支持股票代码精确搜索（如 600900）或股票名称精确搜索（如 长江电力）
- 🕘 **最近使用**：记住当前浏览器会话中最近选择过的股票，便于回到首页后继续操作
- 🗂️ **缓存股票**：展示 `data/` 目录下全部 CSV 缓存股票，无论缓存时间早晚都可直接点击
- 🔥 **热门股票**：展示常用的热门股票卡片，可直接点击选择
- ⚠️ **暂不支持模糊搜索**：需输入完整的股票代码或名称

**股票数据：**
- 内置65+常见A股股票映射（存储在 `gui/stock_list.json`）
- 包含沪深两市主要蓝筹股和热门股票

### 2. 策略选择页面 (`/select_strategy`)

用户旅程的第二步，选择投资策略。

**页面元素：**
- 显示已选择的股票信息（代码和名称）
- 提供"重新选择股票"链接
- 动态展示已注册策略卡片（例如 SMA、均值成本、定投、A50 前夜信号、信号模板）
- 点击策略卡片后，调用API保存策略信息并跳转到运行模式选择页面

### 3. 运行模式选择页面 (`/select_mode`)

用户旅程的第三步，选择运行模式。

**页面元素：**
- 显示面包屑导航，展示当前步骤进度
- 显示已选择的股票和策略信息
- 提供"返回策略选择"链接
- 展示三种运行模式卡片：
  - **回测仿真**（可用）：使用历史数据验证策略效果
  - **实时仿真**（开发中）：使用实时数据模拟交易
  - **实盘交易**（开发中）：连接券商接口实盘交易
- 点击"回测仿真"后，调用API保存运行模式并跳转到**时间段设置页面**（新流程）
- 其他两种模式目前为占位符，点击会提示"功能开发中"

### 3.5. 回测时间段设置页面 (`/select_time_range`) - 新增

用户旅程的第3.5步，设置回测时间段（仅回测模式需要）。

**功能特点：**
- 🗓️ **HTML5日期选择器**：使用原生日期输入控件，直观易用
- ⚡ **快捷时间段选择**：一键设置常用时间段（最近1年、2年、3年、5年、今年至今）
- ✅ **智能验证**：自动验证起始日期不能晚于结束日期
- 📝 **可选填写**：支持留空使用全部历史数据
- 📈 **时间段走势预览**：根据当前日期选择展示该区间日线开盘价走势图
- 💾 **默认优先缓存**：默认先使用本地缓存，减少网络依赖和等待时间
- ♻️ **并行多源重下**：点击清缓存后，会并行尝试全部备选数据源（akshare / baostock / tencent / sina / sohu / eastmoney / cailianpress / stooq）
- 📜 **下载日志可视化**：每个数据源单独一行日志，展示成功/失败、耗时与返回条数
- 🛟 **失败自动降级**：若在线下载失败但存在本地缓存，自动恢复缓存并继续可视化与回测

**页面元素：**
- 显示面包屑导航（已完成：选择股票 → 选择策略 → 选择运行模式 → **当前：设置时间段**）
- 显示已选择的股票、策略和运行模式信息
- 提供"返回运行模式选择"链接
- 时间段说明框：解释时间段的作用和注意事项
- 快捷按钮组：最近1年、2年、3年、5年、今年至今、全部数据（清空）
- 起始日期输入框：HTML5 date类型，可选
- 结束日期输入框：HTML5 date类型，可选
- 日期验证：实时验证，错误时显示提示信息
- 股票走势图：在日期输入区域下方实时展示所选时间段的日线开盘价走势
- 清缓存按钮：清除 `data/` 下全部 CSV 缓存，并重新下载当前股票的日线数据后刷新图表
- 数据源日志：在图表区域显示每个数据源单行下载日志（状态、耗时、条数、错误信息）
- 提交按钮：保存时间段到session并跳转到策略配置页面

**数据格式：**
- 前端使用HTML5 date输入（YYYY-MM-DD格式）
- 提交到后端时自动转换为YYYYMMDD格式
- 保存在session中，/run 回测时优先读取该时间段
- 走势预览使用股票日线数据中的 `open` 字段，按交易日绘制折线图

### 4. SMA 策略配置页面 (`/strategy/sma`)

用户旅程的第五步（原第四步），配置策略参数（以SMA为例）。

**策略说明：**
- 策略原理：基于移动平均线的趋势跟随
- 策略特点：简单有效，适合单边行情
- 参数说明：详细解释 SMA 周期参数

**页面特点：**
- 显示面包屑导航（选择股票 → 选择策略 → 选择运行模式 → **设置时间段** → **配置参数** → 查看结果）
- 显示已选择的股票、策略和运行模式信息
- 提供"返回时间段设置"链接
- **✨ 新增：实时计算显示**
  - 💡 自动获取股票最新价格
  - 💰 实时显示"每单位金额"（股价 × 交易单位）
  - 📊 实时显示"资金一共支持的交易单位数"（初始资金 ÷ 每单位金额）
  - 🔄 参数调整时自动更新计算结果
  - ⚡ 无需提交表单即可预览资金配置是否合理

**可配置参数：**
- ~~股票代码（已在第一步选择）~~
- ~~策略类型（已在第二步选择）~~
- ~~运行模式（已在第三步选择）~~
- ~~起始日期（已在第3.5步设置）~~
- ~~结束日期（已在第3.5步设置）~~
- SMA 周期（默认 20 天）
- 数据源（auto/akshare/baostock）
- 交易单位（默认 100；ETF/场外基金可设为 1 或 0.01）
- 初始资金（默认 100000 元）

### 5. 均值成本策略配置页面 (`/strategy/mean_cost`)

**页面特点：**
- 显示面包屑导航和已选择信息
- 提供"返回时间段设置"链接
- **✨ 新增：实时计算显示**（同SMA策略）
  - 实时显示每单位金额和资金支持交易单位数
  - 参数调整时自动更新

**可配置参数：**
- ~~股票代码（已在第一步选择）~~
- ~~策略类型（已在第二步选择）~~
- ~~运行模式（已在第三步选择）~~
- ~~起始日期（已在第3.5步设置）~~
- ~~结束日期（已在第3.5步设置）~~
- 数据源（auto/akshare/baostock）
- 交易单位（默认 100；ETF/场外基金可设为 1 或 0.01）
- 初始资金（默认 100000 元，建议至少 50000）

### 6. 定投策略配置页面 (`/strategy/fixed_amount`)

**页面特点：**
- 显示面包屑导航和已选择信息
- 提供"返回时间段设置"链接
- **✨ 新增：实时计算显示**（同SMA策略）
  - 实时显示每单位金额、资金支持交易单位数
  - 实时显示“定投金额是一手金额的整数倍”
  - 当定投金额不足买入一手时，整数倍显示为 0 且标红提示
  - 参数调整时自动更新

**可配置参数：**
- ~~股票代码（已在第一步选择）~~
- ~~策略类型（已在第二步选择）~~
- ~~运行模式（已在第三步选择）~~
- ~~起始日期（已在第3.5步设置）~~
- ~~结束日期（已在第3.5步设置）~~
- 每次定投金额（默认 1000 元）
- 数据源（auto/akshare/baostock）
- 交易单位（默认 100；ETF/场外基金可设为 1 或 0.01）
- 初始资金（默认 100000 元）

### 6.1 通用策略配置页面 (`/strategy/<strategy_key>`)

用于自动注册的新策略参数配置（例如 `/strategy/a50_prev_night_1h`）。

**页面特点：**
- 使用统一模板展示策略说明与参数列表
- 参数项来自 `stocks.list_strategy_specs()` 的注册信息
- 支持直接提交到统一回测入口 `/run`
- A50 前夜信号策略默认使用 `CN00Y`（A50期指当月连续）作为期货基准

### 6.2 信号模板策略页面 (`/strategy/signal_template`)

用于“直接填买入、卖出时机”的模板化策略配置。

**页面能力：**
- 买入触发条件下拉：价格条件、指标条件、均线条件、量价条件
- 卖出触发条件下拉：价格条件、指标条件、均线条件、止盈止损
- 条件参数联动显示：根据触发条件自动显示/隐藏对应输入框
- 买入执行方式：全仓买入、固定金额买入、固定仓位买入
- 卖出执行方式：全部卖出、卖出固定数量、卖出比例
- 风险控制（可选）：止盈、止损

**后端行为：**
- 回测时自动计算 MACD/KDJ/RSI/均线/量价等指标
- 按模板条件触发买卖信号，统一走 `stocks.run_backtest` 流程

### 7. 回测进度页面（第五步：执行回测）

**新功能**：提交回测后，会显示可视化进度页，避免长时间无响应，并回放交易动作。

**页面特点：**
- 实时进度条：显示回测处理进度（0-100%）
- 动态状态提示：正在执行、已完成、出错等状态
- 详细进度信息：显示当前处理天数和总天数
- 交易瀑布流：按时间顺序回放每次触发交易的时间、数量、成交金额和资金变化
- 跳过按钮：跳过大约 10 秒的回放动画，直接查看结果
- 放弃按钮：返回参数配置页，不再等待当前回测结果

**技术实现：**
- 使用 Server-Sent Events (SSE) 实时推送进度
- 后台线程执行回测，不阻塞Web请求
- 进度回调机制，每处理一天数据报告一次进度

**用户体验：**
- 避免页面长时间无响应
- 实时了解回测执行状态
- 数据量大时能看到明显的进度更新与交易触发过程
- 完成后自动显示"查看回测结果"按钮

## GUI 测试

- `tests/guitests/test_gui_backtest_report_e2e.py`：主流程截图与报告生成
- `tests/guitests/test_gui_all_strategies_e2e.py`：对 SMA、均值成本、定投、A50 前夜信号、信号模板五种策略分别执行 GUI 全流程回测
- A50 GUI 测试默认使用 `CN00Y`，并会在缺失缓存时预热或生成回退缓存，保证测试稳定性

### 8. 结果展示页面（第六步：查看结果）

运行回测后，系统会展示：
- 股票代码和测试期间
- 初始资金和最终资产
- 收益金额和收益率
- 交易次数和持仓情况
- **交互式资产曲线图表**（包含总资产变化和股价变化，归一化显示）
- 每日历史记录（可选）
- 交易明细列表（可选）

**图表功能：**
- 归一化显示：股价和总资产都以起点为100的相对变化显示
- Y轴：相对变化（起点=100）
- 总资产变化：青色线
- 股价变化：红色线
- 鼠标悬停可同时查看归一化值和原始值
- 两条曲线起点对齐，便于直观对比涨跌幅度

**✨ 新增交互功能（v2.0）：**
- 🔍 **缩放功能**：使用鼠标滚轮对图表X轴进行缩放，精确查看特定时间段
- 🖱️ **平移功能**：按住鼠标左键拖拽图表，在缩放状态下平移查看不同区域
- 🔄 **重置缩放**：点击"重置缩放"按钮一键恢复图表到初始状态
- 💾 **导出图片**：点击"导出图片"按钮将当前图表保存为PNG图片
- 👁️ **图例切换**：点击图表顶部的图例（如"总资产变化"、"股价变化"）可切换显示/隐藏对应的数据曲线
- 📱 **移动端支持**：支持触摸手势进行缩放和平移操作
- 💡 **操作提示**：图表上方显示友好的操作提示信息

## 路由说明

| 路由 | 方法 | 功能 |
|------|------|------|
| `/` | GET | 股票选择页面（首页） |
| `/api/search_stock` | GET | 股票搜索API |
| `/api/select_stock` | POST | 选择股票API（保存到session） |
| `/api/stock_price/<stock_code>` | GET | **获取股票最新价格API（新增）** |
| `/select_strategy` | GET | 策略选择页面 |
| `/api/select_strategy` | POST | 选择策略API（保存到session） |
| `/select_mode` | GET | 运行模式选择页面 |
| `/api/select_mode` | POST | 选择运行模式API（保存到session） |
| `/select_time_range` | GET | **回测时间段设置页面（新增）** |
| `/api/select_time_range` | POST | **保存回测时间段API（新增，保存到session）** |
| `/strategy/sma` | GET | SMA 策略配置页面 |
| `/strategy/mean_cost` | GET | 均值成本策略配置页面 |
| `/strategy/fixed_amount` | GET | 定投策略配置页面 |
| `/run` | POST | 创建回测任务，返回进度页面 |
| `/api/progress/<task_id>` | GET | SSE端点，推送回测进度（实时） |
| `/api/result/<task_id>` | GET | 获取回测任务结果（JSON API） |
| `/view_result` | POST | 查看回测结果页面 |

## 参数说明

### 通用参数

- **symbol**：标的代码（支持股票、ETF、场外基金），如 600900/510300/110011
- **source**：数据源
  - `auto`：自动选择（推荐）
  - `akshare`：使用 AKShare 数据源
  - `baostock`：使用 Baostock 数据源
- **lot**：交易单位（股票常用 100；ETF/场外基金可用 1 或 0.01）
- **cash**：初始资金，单位为元
- **start**：起始日期，格式为 YYYYMMDD 或 YYYY-MM-DD
- **end**：结束日期，格式为 YYYYMMDD 或 YYYY-MM-DD

### 策略特定参数

- **period**（SMA 策略）：移动平均线周期，默认 20 天
- **fixed_amount**（定投策略）：每次定投金额，默认 1000 元

## 客户端验证

所有策略页面都包含日期格式客户端验证：
- 支持 YYYYMMDD 和 YYYY-MM-DD 两种格式
- 验证起始日期不能晚于结束日期
- 实时提示错误信息

## 后端接口

Web 界面通过 `stocks.py` 模块调用后端功能：

```python
# 获取数据
stocks.get_data(symbol, source, start_date, end_date)

# 运行 SMA 回测
stocks.run_sma_backtest(symbol, source, start_date, end_date, lot_size, init_cash, period)

# 运行均值成本回测
stocks.run_mean_cost(symbol, start_date, end_date, lot_size, init_cash, source)

# 运行定投策略回测
stocks.run_fixed_amount(symbol, start_date, end_date, fixed_amount, lot_size, init_cash, source)
```

## 样式设计

- 使用简洁的现代化 CSS 样式
- 响应式设计，支持移动端访问
- 不同策略使用不同的主题色：
  - SMA：蓝色 (#1976d2)
  - 均值成本：橙色 (#ff9800)
  - 定投：绿色 (#4caf50)
- 卡片式布局，悬停效果增强交互体验

## 扩展新策略

如需添加新策略页面：

1. 在 `templates/` 目录创建新页面，如 `strategy_xxx.html`
2. 参考现有策略页面的结构和样式
3. 在 `web.py` 添加路由：
   ```python
   @app.route('/strategy/xxx', methods=['GET'])
   def strategy_xxx():
       return render_template('strategy_xxx.html')
   ```
4. 在 `stocks.py` 的策略注册表中声明新策略参数与执行函数
5. 在 `index.html` 首页添加新策略卡片
6. 如确有必要，再补充专用模板或说明文档

## 测试

### 手动测试

1. 启动 Web 服务
2. 访问 `http://127.0.0.1:5000`
3. 依次点击每个策略卡片，检查页面展示
4. 填写参数并提交表单，验证回测功能
5. 检查结果页面是否正确展示

### 自动化测试

使用 Playwright 进行 UI 测试：

```python
# 示例：测试策略页面导航
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto('http://127.0.0.1:5000')
    
    # 测试导航到 SMA 策略页面
    page.click('text=配置并运行 →')
    assert page.url == 'http://127.0.0.1:5000/strategy/sma'
    
    browser.close()
```

**测试稳定性说明**：
- 关键 UI 元素添加了 `data-testid` 属性以提高 E2E 交互测试的稳定性
- **截图测试**：推荐使用 `page.goto()` 直接导航，避免点击操作的不确定性
- **交互测试**：推荐使用 `data-testid` 或 CSS 类选择器，而非文本选择器（避免 emoji 和文本变化导致的不稳定）
- 完整流程实现详见 `tests/guitests/test_gui_backtest_report_e2e.py`

### GUI 回测报告测试

推荐运行统一的完整流程测试：

```bash
python -m unittest tests.guitests.test_gui_backtest_report_e2e -v
```

运行成功后，截图与 Markdown 报告会统一生成在 `testing/`。

## 依赖

- Flask：Web 框架
- pandas：数据处理
- 统一模拟器：所有策略的回测执行核心
- Chart.js：图表可视化库
- chartjs-plugin-zoom：图表缩放和平移插件
- hammerjs：触摸手势支持库
- 其他依赖见 `requirements.txt`

## 图表交互技术实现

### 使用的库
- **Chart.js v4.x**：现代化的JavaScript图表库
- **chartjs-plugin-zoom v2.0.1**：提供缩放和平移功能
- **Hammer.js v2.0.8**：提供触摸手势支持

### 关键配置

```javascript
// 缩放配置
zoom: {
  zoom: {
    wheel: { enabled: true, speed: 0.1 },  // 鼠标滚轮缩放
    pinch: { enabled: true },               // 触摸捏合缩放
    mode: 'x'                               // 只缩放X轴
  },
  pan: {
    enabled: true,                          // 启用平移
    mode: 'x',                              // 只平移X轴
    modifierKey: null                       // 无需按键，直接拖拽
  },
  limits: {
    x: {min: 'original', max: 'original'}, // 限制在原始范围
    y: {min: 'original', max: 'original'}
  }
}
```

### 功能实现

1. **图例切换**：使用Chart.js内置的图例点击事件处理器
2. **导出图片**：使用`chart.toBase64Image()`方法生成PNG
3. **重置缩放**：调用`chart.resetZoom()`方法
4. **响应式设计**：图表自适应容器大小

## 注意事项

1. **日期格式**：支持 YYYYMMDD 和 YYYY-MM-DD 两种格式
2. **数据源**：首次运行时会自动下载数据并缓存到 `data/` 目录
3. **资金充足**：确保初始资金足够支持策略运行，避免资金不足导致交易失败
4. **回测时间**：数据量大时回测可能需要较长时间，请耐心等待
5. **浏览器兼容**：建议使用现代浏览器（Chrome、Firefox、Safari、Edge）
6. **实时计算**：策略配置页面会自动获取股票最新价格用于计算，使用的是缓存数据的最新收盘价

## 实时计算功能（v2.1新增）

### 功能说明

在所有策略参数配置页面（SMA、均值成本、定投），新增了实时计算功能，帮助用户在提交回测前预览资金配置是否合理。

### 功能特性

1. **自动获取价格**
   - 页面加载时自动调用 `/api/stock_price/<stock_code>` API
   - 返回股票缓存数据中的最新收盘价
   - 显示价格对应的日期供参考

2. **实时计算显示**
   - 💰 **每手金额** = 股票价格 × 每手股数
   - 📊 **资金支持手数** = floor(初始资金 ÷ 每手金额)
   - 🔄 参数调整时自动重新计算（监听 `input` 事件）

3. **视觉反馈**
   - 计算结果显示在黄色高亮区域，醒目易见
   - 当资金不足购买一手时，手数显示为红色警告
   - 当资金充足时，手数显示为绿色正常

4. **安全实现**
   - 使用 `{{ stock_code | tojson }}` 防止XSS攻击
   - 使用 `encodeURIComponent()` 进行URL编码
   - API调用失败时友好提示错误信息

### 技术实现

**后端API**（`gui/web.py`）：
```python
@app.route('/api/stock_price/<stock_code>', methods=['GET'])
def get_stock_price(stock_code):
    """获取股票最新价格API"""
    df = stocks.get_data(symbol=stock_code, source='auto', cache_dir='data')
    latest_price = float(df.iloc[-1]['close'])
    latest_date = str(df.iloc[-1]['date'].date())
    return jsonify({'price': latest_price, 'date': latest_date, 'stock_code': stock_code})
```

**前端JavaScript**（策略模板）：
```javascript
// 获取股票价格
function fetchStockPrice() {
  const url = '/api/stock_price/' + encodeURIComponent(stockCode);
  fetch(url)
    .then(response => response.json())
    .then(data => {
      latestPrice = data.price;
      updateCalculations();
    });
}

// 实时计算
function updateCalculations() {
  const lot = parseInt(lotInput.value) || 100;
  const cash = parseFloat(cashInput.value) || 0;
  const lotAmount = latestPrice * lot;
  const affordableLots = Math.floor(cash / lotAmount);
  // 更新显示...
}

// 监听参数变化
lotInput.addEventListener('input', updateCalculations);
cashInput.addEventListener('input', updateCalculations);
```

### 使用示例

1. 进入任意策略配置页面（如SMA策略）
2. 等待1-2秒，实时计算区域自动显示
3. 修改"每手股数"或"初始资金"参数
4. 观察"每手金额"和"资金支持手数"实时更新
5. 根据计算结果调整参数，确保资金充足

### 截图示例

![实时计算功能截图](https://github.com/user-attachments/assets/d0fd95b7-ee6c-4a68-a310-5701792b4412)

*图：SMA策略配置页面的实时计算功能，显示每手金额2510.00元，资金支持39手*



## 相关模块

- `stocks.py` - 后端业务逻辑
- `simulator/` - 模拟交易引擎
- `solver/` - 策略实现
- `source/` - 数据获取模块
