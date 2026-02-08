# GUI 模块 - Web 界面

## 概述

本模块提供基于 Flask 的 Web 界面，用于可视化配置和运行量化投资策略回测。

## 功能特点

- 🎨 友好的用户界面，无需编写代码即可运行回测
- 📊 支持三种主流投资策略：SMA、均值成本、定投策略
- 🔧 为每种策略提供专门的配置页面，包含详细的策略说明
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
2. **选取策略**：从三种策略中选择一种（SMA、均值成本、定投）
3. **选择运行模式**：选择回测仿真、实时仿真或实盘交易
4. **设置回测时间段**（新增）：使用日期选择器设置回测的起始和结束日期，支持快捷时间段选择
5. **配置策略参数**：设置策略参数、初始资金等（时间段设置已移至上一步）
6. **查看复盘结果**：查看回测结果，包括收益、交易明细等

## 页面说明

### 1. 股票选择页面 (`/`) - 首页

用户旅程的第一步，选择要回测的股票。

**功能特点：**
- 🔍 **搜索功能**：支持股票代码精确搜索（如 600900）或股票名称精确搜索（如 长江电力）
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
- 展示三种策略卡片：
  - **SMA 策略**：简单移动平均策略，趋势跟随
  - **均值成本策略**：低买高卖，适合震荡市场
  - **定投策略**：固定金额投资，降低择时风险
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

**页面元素：**
- 显示面包屑导航（已完成：选择股票 → 选择策略 → 选择运行模式 → **当前：设置时间段**）
- 显示已选择的股票、策略和运行模式信息
- 提供"返回运行模式选择"链接
- 时间段说明框：解释时间段的作用和注意事项
- 快捷按钮组：最近1年、2年、3年、5年、今年至今、全部数据（清空）
- 起始日期输入框：HTML5 date类型，可选
- 结束日期输入框：HTML5 date类型，可选
- 日期验证：实时验证，错误时显示提示信息
- 提交按钮：保存时间段到session并跳转到策略配置页面

**数据格式：**
- 前端使用HTML5 date输入（YYYY-MM-DD格式）
- 提交到后端时自动转换为YYYYMMDD格式
- 保存在session中，/run 回测时优先读取该时间段

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
  - 💰 实时显示"每手金额"（股价 × 每手股数）
  - 📊 实时显示"资金一共支持的手数"（初始资金 ÷ 每手金额）
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
- 每手股数（默认 100）
- 初始资金（默认 100000 元）

### 5. 均值成本策略配置页面 (`/strategy/mean_cost`)

**页面特点：**
- 显示面包屑导航和已选择信息
- 提供"返回时间段设置"链接
- **✨ 新增：实时计算显示**（同SMA策略）
  - 实时显示每手金额和资金支持手数
  - 参数调整时自动更新

**可配置参数：**
- ~~股票代码（已在第一步选择）~~
- ~~策略类型（已在第二步选择）~~
- ~~运行模式（已在第三步选择）~~
- ~~起始日期（已在第3.5步设置）~~
- ~~结束日期（已在第3.5步设置）~~
- 数据源（auto/akshare/baostock）
- 每手股数（默认 100）
- 初始资金（默认 100000 元，建议至少 50000）

### 6. 定投策略配置页面 (`/strategy/fixed_amount`)

**页面特点：**
- 显示面包屑导航和已选择信息
- 提供"返回时间段设置"链接
- **✨ 新增：实时计算显示**（同SMA策略）
  - 实时显示每手金额和资金支持手数
  - 参数调整时自动更新

**可配置参数：**
- ~~股票代码（已在第一步选择）~~
- ~~策略类型（已在第二步选择）~~
- ~~运行模式（已在第三步选择）~~
- ~~起始日期（已在第3.5步设置）~~
- ~~结束日期（已在第3.5步设置）~~
- 每次定投金额（默认 1000 元）
- 数据源（auto/akshare/baostock）
- 每手股数（默认 100）
- 初始资金（默认 100000 元）

### 7. 回测进度页面（第五步：执行回测）

**新功能**：提交回测后，会显示实时进度条页面，避免长时间无响应。

**页面特点：**
- 实时进度条：显示回测处理进度（0-100%）
- 动态状态提示：正在执行、已完成、出错等状态
- 详细进度信息：显示当前处理天数和总天数
- 流畅动画：紫色渐变进度条，平滑过渡

**技术实现：**
- 使用 Server-Sent Events (SSE) 实时推送进度
- 后台线程执行回测，不阻塞Web请求
- 进度回调机制，每处理一天数据报告一次进度

**用户体验：**
- 避免页面长时间无响应
- 实时了解回测执行状态
- 数据量大时能看到明显的进度更新
- 完成后自动显示"查看回测结果"按钮

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

### 9. 历史记录页面 (`/history`)
- **归一化显示**：股价和总资产都以起点为100的相对变化显示
- **Y轴**：相对变化（起点=100）
- **总资产变化**：青色线
- **股价变化**：红色线
- **悬停提示**：鼠标悬停可同时查看归一化值和原始值
- **曲线对齐**：两条曲线起点对齐，便于直观对比涨跌幅度

**✨ 新增交互功能（v2.0）：**
- 🔍 **缩放功能**：使用鼠标滚轮对图表X轴进行缩放，精确查看特定时间段
- 🖱️ **平移功能**：按住鼠标左键拖拽图表，在缩放状态下平移查看不同区域
- 🔄 **重置缩放**：点击"重置缩放"按钮一键恢复图表到初始状态
- 💾 **导出图片**：点击"导出图片"按钮将当前图表保存为PNG图片
- 👁️ **图例切换**：点击图表顶部的图例（如"总资产变化"、"股价变化"）可切换显示/隐藏对应的数据曲线
- 📱 **移动端支持**：支持触摸手势进行缩放和平移操作
- 💡 **操作提示**：图表上方显示友好的操作提示信息

### 8. 历史记录页面 (`/history`)

查看和管理所有回测历史记录：
- 展示最多20条历史回测记录（FIFO策略）
- 显示策略类型、股票代码、回测期间等关键信息
- 支持多选记录进行对比
- 支持删除单条记录
- 自动保存每次回测结果

### 10. 对比页面 (`/compare`)

并排对比多个回测记录：
- 基本信息对比（策略、股票、期间）
- 收益对比（初始资金、最终资产、收益率等）
- 交易统计对比（交易次数、持仓、现金）
- **交互式资产曲线图表对比**（Chart.js可视化）
- 自动标注最优指标

**对比页面图表交互功能：**
- 支持所有与结果页面相同的交互功能（缩放、平移、重置、导出、图例切换）
- 可同时对比多条回测记录的资产曲线
- 点击图例可选择性查看特定记录的曲线

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
| `/history` | GET | 历史记录列表页面 |
| `/compare` | GET | 回测记录对比页面 |
| `/api/records` | GET | 获取记录列表（JSON API） |
| `/api/record/<id>` | GET | 获取单条记录详情（JSON API） |
| `/api/record/<id>` | DELETE | 删除单条记录（JSON API） |

## 参数说明

### 通用参数

- **symbol**：股票代码，如 600900（长江电力）
- **source**：数据源
  - `auto`：自动选择（推荐）
  - `akshare`：使用 AKShare 数据源
  - `baostock`：使用 Baostock 数据源
- **lot**：每手股数，A股市场为 100 股
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
4. 在 `/run` 路由添加策略处理逻辑
5. 在 `index.html` 首页添加新策略卡片
6. 在 `stocks.py` 添加对应的后端函数（如需要）

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
- 关键 UI 元素添加了 `data-testid` 属性以提高测试稳定性
- 历史记录按钮使用 `data-testid="history-link"` 选择器
- 推荐使用 `data-testid` 或 CSS 类选择器，而非文本选择器（避免 emoji 和文本变化导致的不稳定）

### GUI 截图脚本

推荐使用统一入口脚本：

```bash
python tests/guitests/screenshot_main.py main --output screenshots/main_gui.png
python tests/guitests/screenshot_main.py strategy --output-dir screenshots
python tests/guitests/screenshot_main.py history --output-dir screenshots
```

## 依赖

- Flask：Web 框架
- pandas：数据处理
- backtrader：SMA 策略回测
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
