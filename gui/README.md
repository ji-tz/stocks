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
gunicorn -w 4 -b 0.0.0.0:5000 gui.web:app
```

## 页面说明

### 1. 首页 (`/`)

策略选择页面，以卡片形式展示三种策略：

- **SMA 策略**：简单移动平均策略，趋势跟随
- **均值成本策略**：低买高卖，适合震荡市场
- **定投策略**：固定金额投资，降低择时风险

每个卡片包含：
- 策略图标和名称
- 策略简介
- 策略特点标签
- "配置并运行"按钮

### 2. SMA 策略页面 (`/strategy/sma`)

**策略说明：**
- 策略原理：基于移动平均线的趋势跟随
- 策略特点：简单有效，适合单边行情
- 参数说明：详细解释 SMA 周期参数

**可配置参数：**
- 股票代码（必填）
- SMA 周期（默认 20 天）
- 数据源（auto/akshare/baostock）
- 每手股数（默认 100）
- 初始资金（默认 100000 元）
- 起始日期（可选）
- 结束日期（可选）

### 3. 均值成本策略页面 (`/strategy/mean_cost`)

**策略说明：**
- 策略原理：基于平均成本的低买高卖
- 策略特点：自动摊低成本，适合震荡市场
- 适用场景：震荡上行市场，优质股票

**可配置参数：**
- 股票代码（必填）
- 数据源（auto/akshare/baostock）
- 每手股数（默认 100）
- 初始资金（默认 100000 元，建议至少 50000）
- 起始日期（可选）
- 结束日期（可选）

### 4. 定投策略页面 (`/strategy/fixed_amount`)

**策略说明：**
- 策略原理：每天投入固定金额购买股票
- 策略优势：降低择时风险，平滑成本，纪律性强
- 适用场景：长期投资，看好优质标的
- 注意事项：需充足资金，适合优质标的

**可配置参数：**
- 股票代码（必填）
- 每次定投金额（默认 1000 元）
- 数据源（auto/akshare/baostock）
- 每手股数（默认 100）
- 初始资金（默认 100000 元）
- 起始日期（可选）
- 结束日期（可选）

### 5. 结果展示页面

运行回测后，系统会展示：
- 股票代码和测试期间
- 初始资金和最终资产
- 收益金额和收益率
- 交易次数和持仓情况
- **资产曲线图表**（包含总资产线和股价波动线，双Y轴显示）
- 每日历史记录（可选）
- 交易明细列表（可选）

**图表功能：**
- 左侧Y轴：总资产（元）- 青色线
- 右侧Y轴：股价（元）- 红色线
- 鼠标悬停可同时查看两条线的数值
- 直观对比资产变化与股价波动的关系
### 6. 历史记录页面 (`/history`)

查看和管理所有回测历史记录：
- 展示最多20条历史回测记录（FIFO策略）
- 显示策略类型、股票代码、回测期间等关键信息
- 支持多选记录进行对比
- 支持删除单条记录
- 自动保存每次回测结果

### 7. 对比页面 (`/compare`)

并排对比多个回测记录：
- 基本信息对比（策略、股票、期间）
- 收益对比（初始资金、最终资产、收益率等）
- 交易统计对比（交易次数、持仓、现金）
- 资产曲线图表对比（Chart.js可视化）
- 自动标注最优指标

## 路由说明

| 路由 | 方法 | 功能 |
|------|------|------|
| `/` | GET | 首页，策略选择 |
| `/strategy/sma` | GET | SMA 策略配置页面 |
| `/strategy/mean_cost` | GET | 均值成本策略配置页面 |
| `/strategy/fixed_amount` | GET | 定投策略配置页面 |
| `/run` | POST | 执行回测，返回结果页面，自动保存记录 |
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

## 依赖

- Flask：Web 框架
- pandas：数据处理
- backtrader：SMA 策略回测
- 其他依赖见 `requirements.txt`

## 注意事项

1. **日期格式**：支持 YYYYMMDD 和 YYYY-MM-DD 两种格式
2. **数据源**：首次运行时会自动下载数据并缓存到 `data/` 目录
3. **资金充足**：确保初始资金足够支持策略运行，避免资金不足导致交易失败
4. **回测时间**：数据量大时回测可能需要较长时间，请耐心等待
5. **浏览器兼容**：建议使用现代浏览器（Chrome、Firefox、Safari、Edge）

## 相关模块

- `stocks.py` - 后端业务逻辑
- `simulator/` - 模拟交易引擎
- `solver/` - 策略实现
- `source/` - 数据获取模块
