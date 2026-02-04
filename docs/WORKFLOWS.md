# CI/CD 工作流架构说明

## 概述

本项目采用三个独立的 GitHub Actions 工作流，实现完整的持续集成和持续交付（CI/CD）流程。

```
┌─────────────────────────────────────────────────────────────────┐
│                     代码提交 / Pull Request                       │
└────────┬───────────────────────┬────────────────────┬───────────┘
         │                       │                    │
         ▼                       ▼                    ▼
┌────────────────┐      ┌────────────────┐   ┌────────────────┐
│  🔍 Lint       │      │  🧪 Test       │   │  📦 Package    │
│  代码检视       │      │  自动化测试     │   │  自动化打包     │
└────────┬───────┘      └────────┬───────┘   └────────┬───────┘
         │                       │                    │
         ▼                       ▼                    ▼
    质量保证                  功能验证              产物归档
```

## 工作流详细说明

### 1. 🔍 Lint 工作流

**文件**: `.github/workflows/lint.yml`

**目的**: 代码质量检查，确保代码符合规范和最佳实践

**触发条件**:
- Push 到 main 分支
- 创建或更新 Pull Request

**执行步骤**:
1. 检出代码
2. 设置 Python 3.12 环境
3. 配置 pip 镜像源（中国镜像）
4. 安装检查工具和项目依赖
5. 运行 Pylint - Python 代码规范检查
6. 运行 Flake8 - 代码风格和语法检查
7. 运行 Mypy - 静态类型检查

**特点**:
- 所有检查都设置为 `continue-on-error: true`，不阻塞流程
- 快速反馈代码质量问题
- 独立运行，不依赖其他工作流

**运行时间**: ~2-3 分钟

---

### 2. 🧪 Test 工作流

**文件**: `.github/workflows/test.yml`

**目的**: 全面的自动化测试，包括单元测试、集成测试、界面测试

**触发条件**:
- Push 到 main 分支
- 创建或更新 Pull Request

**权限要求**:
- `contents: write` - 提交测试截图到 PR 分支
- `pull-requests: write` - 在 PR 中发布评论

**执行步骤**:
1. 检出代码（使用 PR head ref）
2. 设置 Python 3.12 环境
3. 安装项目依赖和 Playwright
4. **运行所有单元测试** (`tests/` 目录)
5. **运行策略模拟器测试**
6. **验证策略加载功能**
7. **主界面自动截图** (使用 Playwright)
8. **长江电力集成测试** (2020-2022定投回测)
9. 上传截图到 Artifacts (`test-screenshots`)
10. 上传测试结果到 Artifacts (`test-results`)
11. 提交截图到 PR 分支（如果是 PR）
12. **在 PR 中自动评论测试报告**

**输出产物**:
- `screenshots/main_gui.png` - 主界面截图
- `screenshots/yangtze_power_test.png` - 测试结果图表
- `test_results/yangtze_power_test.json` - 详细测试数据

**PR 评论内容**:
- 主界面截图展示
- 长江电力测试详细数据（初始资金、最终资产、收益率等）
- 测试结果图表
- Artifacts 下载链接

**特点**:
- 完整的测试覆盖
- 可视化测试结果
- 自动化 PR 反馈
- 测试产物持久化保存（30天）

**运行时间**: ~5-8 分钟

---

### 3. 📦 Package 工作流

**文件**: `.github/workflows/package.yml`

**目的**: 打包发布，构建分发包和归档测试产物

**触发条件**:
- Push 到 main 分支
- 创建或更新 Pull Request
- Push tag (如 `v1.0.0`)
- 手动触发 (workflow_dispatch)

**权限要求**:
- `contents: write` - 创建 GitHub Release

**执行步骤**:
1. 检出代码
2. 设置 Python 3.12 环境
3. 安装项目依赖
4. **创建源代码压缩包**
   - 排除 `.git`, `__pycache__`, `.venv` 等无关文件
   - 命名格式: `stocks-source-{commit-sha}.tar.gz`
5. **创建依赖文件包**
   - `requirements.txt` - 基础依赖
   - `requirements-freeze.txt` - 完整版本锁定
   - `INSTALL.md` - 详细安装说明
6. **打包测试产物**
   - 测试截图归档
   - 测试结果归档
7. **生成打包清单** (`MANIFEST.md`)
   - 构建时间、Git 信息
   - 所有文件列表及大小
8. 上传所有打包文件到 Artifacts
9. **创建 GitHub Release**（仅在 tag 推送时）
   - 附带源代码包、依赖文件、文档
   - 自动生成发布说明

**输出产物**:
- `stocks-source-{sha}.tar.gz` - 完整源代码包
- `requirements.txt` - 项目依赖
- `requirements-freeze.txt` - 版本锁定依赖
- `INSTALL.md` - 安装说明
- `MANIFEST.md` - 打包清单
- `screenshots-{sha}.tar.gz` - 测试截图（如存在）
- `test-results-{sha}.tar.gz` - 测试结果（如存在）

**特点**:
- 完整的发布包构建
- 支持自动发布到 GitHub Releases
- 测试产物归档
- 清晰的文档和清单
- 产物保留 90 天

**运行时间**: ~3-4 分钟

---

## 工作流执行流程图

### Pull Request 流程

```
PR 创建/更新
    │
    ├──→ 🔍 Lint (并行)
    │    ├─ Pylint
    │    ├─ Flake8
    │    └─ Mypy
    │
    ├──→ 🧪 Test (并行)
    │    ├─ 单元测试
    │    ├─ 集成测试
    │    ├─ 界面截图
    │    ├─ 长江电力测试
    │    ├─ 提交截图到分支
    │    └─ 评论测试报告到 PR
    │
    └──→ 📦 Package (并行)
         ├─ 打包源代码
         ├─ 创建依赖文件
         ├─ 生成文档
         └─ 上传 Artifacts
```

### Tag 推送流程

```
Tag 推送 (v1.0.0)
    │
    ├──→ 🔍 Lint
    ├──→ 🧪 Test
    └──→ 📦 Package
         └─ 创建 GitHub Release
            ├─ 源代码包
            ├─ 依赖文件
            └─ 文档说明
```

## 配置文件

### Lint 配置
- `.pylintrc` - Pylint 规则配置
- `.flake8` - Flake8 规则配置
- `mypy.ini` - Mypy 类型检查配置

### 依赖配置
- `pip.conf` - pip 中国镜像源配置
- `requirements.txt` - 项目依赖列表

### Git 配置
- `.gitignore` - 忽略规则
  - `__pycache__/`
  - `.venv/`
  - `screenshots/`
  - `test_results/`
  - `dist/`
  - `build/`

## 最佳实践

### 开发者工作流

1. **本地开发**
   ```bash
   # 运行 lint
   pylint --rcfile=.pylintrc stocks.py main.py
   flake8 .
   mypy stocks.py main.py
   
   # 运行测试
   python -m unittest discover tests -v
   ```

2. **提交代码**
   ```bash
   git checkout -b feature/my-feature
   # ... 做出修改 ...
   git commit -m "feat: add new feature"
   git push origin feature/my-feature
   ```

3. **创建 PR**
   - 自动触发所有三个工作流
   - 查看 PR 中的自动评论，了解测试结果
   - 从 Artifacts 下载详细报告

4. **发布版本**
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
   - 自动创建 GitHub Release
   - 包含所有打包文件

## 监控和调试

### 查看工作流状态
- 访问 GitHub Actions 页面
- 每个工作流独立显示状态

### 下载产物
- Test 工作流: `test-screenshots`, `test-results` (30天)
- Package 工作流: `package-{sha}` (90天)

### 调试失败
- 查看具体步骤的日志
- 下载 Artifacts 分析测试结果
- 本地重现问题

## 性能优化

### 并行执行
- 三个工作流完全并行，互不依赖
- 总运行时间约为最长工作流的时间（~8分钟）

### 缓存策略
- pip 包由 GitHub Actions 自动缓存
- Playwright 浏览器自动缓存

### 资源使用
- 所有工作流使用 ubuntu-latest runner
- Python 3.12 环境
- 轻量级依赖安装

## 安全考虑

### 权限最小化
- Lint: 无需特殊权限
- Test: 仅需写入权限用于提交截图和评论
- Package: 仅需写入权限用于创建 Release

### 密钥管理
- 使用 GitHub 自动提供的 `GITHUB_TOKEN`
- 无需额外配置密钥

### 代码安全
- 所有工作流代码公开可审查
- 依赖来源清晰（requirements.txt）
- 使用官方 GitHub Actions

## 未来扩展

### 可能的增强
1. **Lint 工作流**
   - 添加更多静态分析工具
   - 集成安全扫描
   - 代码覆盖率报告

2. **Test 工作流**
   - 性能测试
   - 压力测试
   - 更多集成测试场景

3. **Package 工作流**
   - Docker 镜像构建
   - PyPI 包发布
   - 文档站点部署

### 集成建议
- 集成 CodeQL 安全扫描
- 添加依赖更新检查
- 集成 SonarCloud 代码质量分析

---

**文档版本**: 1.0  
**最后更新**: 2024-02-04  
**维护者**: Copilot AI Coding Agent
