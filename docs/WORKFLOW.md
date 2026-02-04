# GitHub Actions 工作流文档

本文档详细说明项目的 GitHub Actions 自动化工作流配置和功能。

## 工作流文件

位置：`.github/workflows/python-package.yml`

## 触发条件

工作流在以下情况下自动触发：
- Push到 `main` 分支
- Pull Request到 `main` 分支

## 权限配置

```yaml
permissions:
  contents: read          # 读取仓库内容
  pull-requests: write    # 写入PR评论
```

## 工作流步骤详解

### 1. 环境准备

使用 Python 3.12 版本，确保环境一致性。

### 2. 依赖安装

安装所有Python依赖和Playwright浏览器。

### 3. 静态代码检查

#### 3.1 Pylint检查
- 代码规范性
- 命名约定
- 代码复杂度
- 潜在错误

#### 3.2 Flake8检查
- PEP 8 代码风格
- 语法错误
- 未使用的导入
- 代码格式问题

#### 3.3 Mypy类型检查
- 类型注解一致性
- 类型错误
- 函数签名

**注意**: 所有静态检查步骤使用 `continue-on-error: true`，即使检查失败也不会阻止后续步骤。

### 4. 单元测试

运行所有 `tests/` 目录下的单元测试。

### 5. 主界面截图

功能：
- 启动Flask应用
- 使用Playwright访问主界面
- 截取全页面截图
- 保存到 `screenshots/main_gui.png`

### 6. 长江电力集成测试

测试内容：
- 股票代码：600900（长江电力）
- 测试期间：2020-2022年
- 策略：定投（Mean Cost DCA）
- 输出：收益图表和统计数据

### 7. 上传Artifacts

上传截图和测试结果，保留30天。

### 8. PR评论

在Pull Request中自动发布测试报告，包含：
- 主界面截图说明
- 长江电力测试结果摘要
- Artifacts下载链接

## 本地运行

```bash
# 1. 安装依赖
pip install -r requirements.txt
playwright install chromium

# 2. 运行静态检查
pylint --rcfile=.pylintrc stocks.py main.py gui/ simulator/ solver/ tests/
flake8 .
mypy stocks.py main.py --config-file=mypy.ini

# 3. 运行测试
python -m unittest discover tests -v

# 4. 主界面截图
python screenshot_main.py screenshots/main_gui.png

# 5. 运行集成测试
python test_yangtze_power.py
```
