# 从 Test 工作流中移除 GUI 相关步骤

## 修改概述

根据 PR 评论要求，从 `.github/workflows/test.yml` 中移除所有与 GUI 相关的步骤，仅保留其它测试。同时同步更新了相关文档。

## 修改内容

### 1. `.github/workflows/test.yml` (主要修改)

#### 删除的步骤：
1. **Playwright 依赖安装** (第 38-39 行)
   - 删除了 `playwright install chromium`
   - 删除了 `playwright install-deps chromium`

2. **GUI 截图步骤** (第 65-77 行)
   - 删除了 "Take Main GUI Screenshot"
   - 删除了 "Take Strategy Config Screenshots"
   - 删除了 "Take History Feature Screenshots"

3. **时间范围选择截图** (第 84-87 行)
   - 删除了 "Take Time Range Selection Screenshots"

4. **截图上传步骤** (第 89-95 行)
   - 删除了 "Upload Screenshots" 步骤（上传到 Artifacts）

#### 保留的步骤：
✓ 单元测试 (Run all tests)
✓ 策略模拟器测试 (Run strategy simulator tests)
✓ 模拟器功能验证 (Verify simulator functionality)
✓ 股票集成测试 (Run Stock Integration Test)
✓ 测试结果上传 (Upload Test Results)
✓ 测试日志上传 (Upload Test Logs)
✓ PR 评论测试报告 (Comment PR with Test Results)

### 2. `README.md` (文档同步更新)

**位置**：第 310-328 行（Test 工作流说明部分）

**修改内容**：
- 删除了测试内容第 4 项："界面测试 - 主界面自动截图"
- 删除了输出产物中的："测试截图上传到 Artifacts"

### 3. `.github/workflows/README.md` (文档同步更新)

**修改内容**：
- 更新工作流描述：将 `test.yml` 从"单元测试 + 集成测试 + GUI截图测试"改为"单元测试 + 集成测试"
- 删除 test.yml 产物中的截图描述：
  - 删除："截图：包括主界面、策略配置、历史记录、股价图表、时间段设置等完整截图"
  - 删除 Artifacts 中的 `test-screenshots`

## 修改统计

```
.github/workflows/README.md |  5 ++---
.github/workflows/test.yml  | 29 -----------------------------
README.md                   |  2 --
3 files changed, 2 insertions(+), 34 deletions(-)
```

**总计**：删除 34 行，新增 2 行

## 验证

✓ YAML 语法检查通过
✓ 所有非 GUI 测试步骤保留
✓ GUI 专用工作流 `testgui.yml` 不受影响
✓ 文档描述与实际代码一致

## 影响范围

### 不受影响：
- ✓ 单元测试功能完整保留
- ✓ 策略测试功能完整保留
- ✓ 集成测试功能完整保留
- ✓ PR 评论测试报告功能保留
- ✓ GUI 截图功能由专用的 `testgui.yml` 工作流提供

### 移除功能：
- ✗ Test 工作流中不再执行 GUI 截图
- ✗ Test 工作流中不再上传截图 Artifacts
- ✗ Test 工作流中不再需要安装 Playwright

## 设计理念

此修改符合职责分离原则：
- **test.yml**: 专注于单元测试、策略测试、集成测试
- **testgui.yml**: 专注于 GUI 截图和可视化测试

这样可以：
1. 加快 test.yml 的执行速度（不需要安装 Playwright 和浏览器）
2. 降低 test.yml 的复杂度
3. 更清晰的工作流职责划分
4. 方便独立调试和维护

## 后续建议

如果需要在 test.yml 中重新添加 GUI 相关测试，建议：
1. 重新添加 Playwright 安装步骤
2. 恢复相关截图步骤
3. 更新文档说明

---
*修改完成时间: 2025-01-XX*
*修改人: Kiki (AI Assistant)*
