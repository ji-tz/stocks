# 测试文档

本目录包含项目的所有测试文件，确保代码质量和功能正确性。

## 测试文件结构

### 核心功能测试
- `test_main.py` - 测试主模块的数据获取功能
- `test_stocks.py` - 测试 stocks 模块的核心业务逻辑
- `test_integration.py` - 集成测试，验证 Backtrader 回测功能

### 策略与模拟器测试
- **`test_simulator.py`** - **[新增]** 全面测试模拟交易系统
  - 测试 `Simulator` 基础类功能
  - 测试 `MeanCostDecision` 均值成本策略
  - 测试 `SmaDecision` 简单移动平均策略
  - 测试不同参数配置（lot_size, init_cash）
  - 测试买卖逻辑和盈亏计算
  - 端到端集成测试

- `test_run_sma.py` - 测试 SMA 回测运行功能

### 数据源测试
- `test_data_provider_cache.py` - 测试数据提供者缓存功能
- `test_cache_utils.py` - 测试缓存工具函数

### 界面测试
- `test_gui_app.py` - 测试 Flask Web 界面路由
- `test_main_run.py` - 测试主程序启动
- `test_screenshot_cli.py` - 截图脚本 CLI 逻辑测试

## 运行测试

### 运行所有测试
```bash
python -m unittest discover tests
```

### 运行详细输出模式
```bash
python -m unittest discover tests -v
```

### 运行特定测试文件
```bash
# 运行模拟器测试
python -m unittest tests.test_simulator -v

# 运行策略测试
python -m unittest tests.test_run_sma -v
```

### 运行特定测试类或方法
```bash
# 运行特定测试类
python -m unittest tests.test_simulator.TestMeanCostStrategy -v

# 运行特定测试方法
python -m unittest tests.test_simulator.TestMeanCostStrategy.test_mean_cost_decision_first_buy -v
```

## 测试覆盖范围

### 模拟器测试（test_simulator.py）- 20个测试用例

#### 1. Simulator 基础功能 (3个测试)
- ✅ 初始化参数验证
- ✅ DataFrame 必需性检查
- ✅ 空 DataFrame 处理

#### 2. MeanCostDecision 策略 (6个测试)
- ✅ 首次买入决策（持仓为0）
- ✅ 价格低于平均成本时买入
- ✅ 价格高于平均成本时卖出
- ✅ 价格等于平均成本时持有
- ✅ 基本模拟流程
- ✅ 多次交易模拟

#### 3. SmaDecision 策略 (4个测试)
- ✅ 收盘价高于 SMA 时买入
- ✅ 持仓且收盘价低于 SMA 时卖出
- ✅ 无 DataFrame 时的处理
- ✅ 基本模拟流程

#### 4. 参数化测试 (3个测试)
- ✅ 不同交易手数（lot_size）
- ✅ 不同初始资金（init_cash）
- ✅ 资金不足时阻止买入

#### 5. 集成测试 (2个测试)
- ✅ MeanCost 策略端到端流程
- ✅ SMA 策略端到端流程

#### 6. 盈亏计算测试 (2个测试)
- ✅ 卖出时实现盈利计算
- ✅ 持仓时未实现盈利计算

## CI/CD 集成

测试已集成到 GitHub Actions workflow (`.github/workflows/python-package.yml`)：

1. **自动运行所有测试** - 每次 push 到 main 分支或创建 PR 时
2. **详细输出模式** - 显示每个测试的运行状态
3. **专项策略测试** - 单独运行策略模拟器测试
4. **模块加载验证** - 验证策略模块可正确导入

## 测试数据

测试使用模拟数据（mock data），不依赖外部 API：
- 使用 `unittest.mock.patch` 模拟数据源
- 使用 `make_test_df()` 生成测试用价格数据
- 价格数据包含：date, open, high, low, close, volume

## 测试最佳实践

1. **隔离性** - 每个测试相互独立，不依赖执行顺序
2. **可重复性** - 使用固定的测试数据，结果可预测
3. **快速执行** - 使用 mock 避免网络请求，测试快速完成
4. **全面覆盖** - 覆盖正常流程、边界条件、异常情况
5. **清晰命名** - 测试方法名称明确说明测试内容
6. **中文注释** - 使用中文 docstring 说明测试目的

## 添加新测试

添加新测试时请遵循以下规范：

1. 在相应的测试文件中添加测试方法
2. 使用 `unittest.TestCase` 作为基类
3. 测试方法名以 `test_` 开头
4. 添加中文 docstring 说明测试目的
5. 使用 `self.assert*` 方法进行断言
6. 运行测试确保通过后再提交

## 贡献指南

如需添加新功能，请：
1. 先编写测试用例（TDD 方式）
2. 实现功能代码
3. 确保所有测试通过
4. 更新本文档（如适用）
