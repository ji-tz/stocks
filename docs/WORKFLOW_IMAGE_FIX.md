# Workflow 图片显示修复文档

## 问题描述

在 PR 中，`testgui.yml` workflow 自动生成的评论不包含截图图片，只显示文件信息和下载链接。

## 问题原因

在 `.github/workflows/testgui.yml` 的 "Comment PR with Screenshots" 步骤中，代码引用了一个不存在的步骤输出：

```javascript
const uploaded = '${{ steps.upload_to_public_repo.outputs.uploaded }}' === 'true';
const baseUrl = '${{ steps.upload_to_public_repo.outputs.base_url }}';
```

由于 `upload_to_public_repo` 步骤不存在：
- `uploaded` 变量永远是 `false`（空字符串不等于 'true'）
- `baseUrl` 变量永远是空字符串
- 所有的 `if (uploaded && baseUrl)` 条件判断都失败
- 导致只能显示文件信息而不是图片

## 解决方案

使用 base64 编码将图片直接嵌入 Markdown 评论中，无需外部托管。

### 实现细节

1. **添加辅助函数**：
   - `imageToDataUrl(imagePath)`: 将图片转换为 base64 Data URL
   - `formatImageDisplay(imagePath, title)`: 统一处理图片显示逻辑

2. **智能显示策略**：
   - 小于 1MB 的图片：使用 base64 Data URL 嵌入显示
   - 大于等于 1MB 的图片：显示文件信息和 Artifacts 下载链接
   - 不存在的图片：显示警告信息

3. **代码示例**：

```javascript
// 函数：将图片转换为 base64 data URL（用于小图片）
function imageToDataUrl(imagePath) {
  try {
    if (!fs.existsSync(imagePath)) {
      return null;
    }
    const imageBuffer = fs.readFileSync(imagePath);
    const base64Image = imageBuffer.toString('base64');
    // 检测图片格式
    const ext = path.extname(imagePath).toLowerCase();
    const mimeType = ext === '.png' ? 'image/png' : 'image/jpeg';
    return `data:${mimeType};base64,${base64Image}`;
  } catch (error) {
    console.log(`Error converting image to data URL ${imagePath}: ${error.message}`);
    return null;
  }
}

// 函数：格式化图片显示（使用 base64 或回退到文件信息）
function formatImageDisplay(imagePath, title) {
  if (!fs.existsSync(imagePath)) {
    return `⚠️ ${title}未生成`;
  }
  
  const stats = fs.statSync(imagePath);
  const sizeKB = (stats.size / 1024).toFixed(1);
  const filename = path.basename(imagePath);
  
  // 如果图片小于 1MB，使用 base64 嵌入
  if (stats.size < 1024 * 1024) {
    const dataUrl = imageToDataUrl(imagePath);
    if (dataUrl) {
      return `![${title}](${dataUrl})\n\n*${filename} - ${sizeKB} KB*`;
    }
  }
  
  // 否则显示文件信息和下载链接
  return `**${title}** (${filename}) - ${sizeKB} KB - [从 Artifacts 下载](${artifactUrl})`;
}
```

### 优点

1. ✅ **无需外部依赖**：不需要额外的公开仓库或图床服务
2. ✅ **图片直接显示**：在 PR 评论中直接看到截图，无需下载
3. ✅ **向后兼容**：大图片仍然提供 Artifacts 下载链接
4. ✅ **健壮性高**：有完善的错误处理和回退机制
5. ✅ **最小改动**：只修改图片处理逻辑，不影响其他功能

### 缺点与限制

1. ⚠️ **评论大小**：base64 编码会使图片体积增大约 33%，但 GitHub 单条评论限制为 65536 字符，对于多个小截图仍然足够
2. ⚠️ **大图片限制**：大于 1MB 的图片仍然需要从 Artifacts 下载

## 测试验证

添加了完整的单元测试 `tests/test_workflow_image_display.py`：

```bash
# 运行测试
python -m unittest tests.test_workflow_image_display -v
```

测试覆盖：
- ✅ 小图片 base64 编码
- ✅ 大图片大小检查
- ✅ 图片文件存在性
- ✅ 文件大小格式化
- ✅ 图片格式检测
- ✅ Markdown 语法生成
- ✅ Workflow 配置结构

## 修改文件清单

1. `.github/workflows/testgui.yml` - 主要修复
2. `.github/workflows/README.md` - 文档更新
3. `tests/test_workflow_image_display.py` - 新增测试
4. `docs/WORKFLOW_IMAGE_FIX.md` - 本文档

## 验证步骤

1. **本地验证**：
   ```bash
   # 验证 YAML 语法
   python3 -c "import yaml; yaml.safe_load(open('.github/workflows/testgui.yml'))"
   
   # 运行测试
   python -m unittest tests.test_workflow_image_display -v
   ```

2. **PR 验证**：
   - 创建一个测试 PR
   - 等待 `testgui.yml` workflow 运行完成
   - 检查 PR 评论中是否正常显示截图

## 技术细节

### Base64 Data URL 格式

```
data:[<mediatype>][;base64],<data>
```

示例：
```
data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB...
```

### GitHub Markdown 支持

GitHub 的 Markdown 渲染器支持 base64 Data URL 格式的图片：

```markdown
![Alt Text](data:image/png;base64,iVBORw0KGgoAAAANS...)
```

### 性能考虑

- PNG 截图通常在 50-500 KB 范围内
- Base64 编码后约 67-667 KB
- 5-10 张截图总大小约 3-7 MB（base64）
- GitHub 评论限制：65536 字符 ≈ 64 KB
- **实际情况**：需要注意不要在单条评论中嵌入太多图片

### 改进建议

如果未来需要支持更多或更大的图片，可以考虑：

1. **分页显示**：将截图分散到多条评论中
2. **外部托管**：使用 GitHub Release Assets 或其他图床
3. **压缩优化**：在截图生成时就进行压缩

## 参考资料

- [GitHub Actions - github-script](https://github.com/actions/github-script)
- [Data URLs - MDN](https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/Data_URLs)
- [GitHub Markdown Spec](https://github.github.com/gfm/)
- [GitHub API - Issues Comments](https://docs.github.com/en/rest/issues/comments)

## 更新记录

- 2024-02-08：初始版本，修复图片显示问题
