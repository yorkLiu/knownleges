# Telegraph-Image 图床集成文档

## 概述

本项目现已集成 Telegraph-Image 图床，用于存储 X/Twitter 推文图片，替代本地图片存储方案。

**图床地址**: https://telegraph-image-fork.pages.dev

## 优势

1. **免费无限存储**: 基于 Telegram 和 Cloudflare Pages
2. **全球 CDN 加速**: Cloudflare 全球节点
3. **自动生成 URL**: 上传后自动返回可访问的图片链接
4. **智能去重**: 使用缓存避免重复上传相同图片
5. **视频友好**: 自动识别并跳过视频缩略图

## 文件说明

### 核心脚本

1. **upload_to_telegraph.py** - 基础上传工具
   ```bash
   # 上传单张图片
   python upload_to_telegraph.py /path/to/image.jpg
   
   # 生成 Markdown 格式
   python upload_to_telegraph.py --md post.md /path/to/image.jpg "图片描述"
   ```

2. **upload_images_integration.py** - 批量处理 MD 文件
   ```bash
   # 处理所有 MD 文件
   python upload_images_integration.py --all
   
   # 处理指定文件
   python upload_images_integration.py file1.md file2.md
   
   # 不使用缓存（强制重新上传）
   python upload_images_integration.py --all --no-cache
   
   # 静默模式
   python upload_images_integration.py --all -q
   ```

3. **upload_images_to_telegraph.py** - 旧版本，保留用于兼容性

### 配置文件

- **telegraph_cache.json**: 上传缓存文件，记录已上传图片的本地路径和 Telegraph URL
  - 位置：`/home/hermes/workspace/knownleges/X/scripts/telegraph_cache.json`
  - 格式：`{"本地绝对路径": "Telegraph URL"}`

## 使用场景

### 场景 1：爬虫抓取后自动上传（推荐）

在 `fetch_x_users.py` 的 `download_image()` 函数中，下载成功后会自动调用图床上传：

```python
# 修改 download_image 函数
def download_image(image_url, username, retry=5):
    # ... 下载逻辑 ...
    
    # 下载成功后上传到图床
    if success:
        local_path = IMAGES_DIR / f"{username}/{image_id}"
        telegraph_url = upload_to_telegraph(local_path)
        if telegraph_url:
            return (True, telegraph_url)  # 返回图床 URL
    # ... 其余逻辑 ...
```

### 场景 2：批量处理现有 MD 文件

已有 MD 文件中的图片仍使用本地路径，可以批量转换为图床 URL：

```bash
cd /home/hermes/workspace/knownleges/X/scripts

# 处理所有 2026 年的推文文件
python upload_images_integration.py --all

# 只处理特定用户的文件
python upload_images_integration.py ../../docs/x_post_data/elonmusk_2026.md

# 查看帮助
python upload_images_integration.py --help
```

### 场景 3：手动上传单张图片

```bash
# 上传图片并获取 URL
python upload_to_telegraph.py /path/to/image.png

# 输出示例：
# 📤 正在上传：image.png...
# ✅ 上传成功：https://telegraph-image-fork.pages.dev/file/xxx.png
# ✅ 图床 URL：https://telegraph-image-fork.pages.dev/file/xxx.png
```

## MD 文件格式转换示例

### 转换前（本地路径）
```markdown
<img src="/images/elonmusk/media_HJg1dugWIAQfkEU.jpg" alt="图片 1" style="max-width:100%;border-radius:8px;margin:8px 0;">
```

### 转换后（图床 URL）
```markdown
<img src="https://telegraph-image-fork.pages.dev/file/AgACAgUAAxkDAAMJahpPpc2bKWS43WOAQdYxzA3LSa8AApcQaxsTQtFUKFL1ciSbLYwBAAMCAAN5AAM7BA.jpg" alt="图片 1" style="max-width:100%;border-radius:8px;margin:8px 0;">
```

## 特殊处理

### 视频缩略图

脚本会自动识别并跳过视频缩略图，保留原始 nitter 链接。视频缩略图包含以下关键词：

- `amplify_video_thumb`
- `ext_tw_video_thumb`
- `video_thumb`

### 缓存机制

为避免重复上传相同图片，脚本使用 JSON 缓存：

- **首次上传**: 图片上传到 Telegraph，URL 保存到缓存
- **后续使用**: 相同图片直接从缓存读取 URL，无需重新上传
- **缓存位置**: `X/scripts/telegraph_cache.json`
- **清除缓存**: 删除缓存文件或使用 `--no-cache` 参数

## 性能优化

### 批量处理

处理多个 MD 文件时，脚本会：

1. 自动去重同一文件中的重复图片
2. 跨文件复用缓存
3. 智能跳过视频缩略图

### 并发上传

目前使用串行上传，如果需要加速处理大量图片，可以考虑：

```python
# 修改 upload_images_integration.py，添加并发控制
from concurrent.futures import ThreadPoolExecutor

# 使用线程池并发上传（注意：不要超过 Telegram 速率限制）
```

## 故障排查

### 上传失败

1. **检查网络连接**: Telegraph 服务托管在 Cloudflare 上
   ```bash
   curl -I https://telegraph-image-fork.pages.dev
   ```

2. **检查文件权限**: 确保图片文件可读
   ```bash
   ls -la /home/hermes/workspace/knownleges/docs/public/images/
   ```

3. **检查文件格式**: 仅支持常见图片格式
   - `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.bmp`

### 替换失败

如果提示 "替换失败（未找到匹配）"，可能是：

1. MD 文件中图片格式不一致
2. 路径中包含特殊字符
3. 图片在同一文件中出现多次

解决方案：检查 MD 文件中图片标签的实际格式，调整正则表达式。

## API 参考

### Telegraph-Image 上传 API

**端点**: `https://telegraph-image-fork.pages.dev/upload`

**方法**: `POST`

**参数**: `file` (表单字段)

**响应**:
```json
[{
  "src": "/file/{file_id}.{ext}"
}]
```

**完整 URL**: `https://telegraph-image-fork.pages.dev/file/{file_id}.{ext}`

### curl 示例

```bash
curl -X POST https://telegraph-image-fork.pages.dev/upload \
  -F 'file=@image.jpg' \
  -H 'User-Agent: Mozilla/5.0'
```

## 维护

### 更新缓存

当手动删除或移动图片文件时，需要更新缓存：

```bash
# 清理缓存
rm /home/hermes/workspace/knownleges/X/scripts/telegraph_cache.json

# 重新生成缓存
python upload_images_integration.py --all --no-cache
```

### 监控上传统计

每次运行脚本都会生成统计报告：

```
============================================================
📊 汇总统计
============================================================
总图片数：52
♻️  从缓存：36
✅ 新上传：16
⏭️  跳过视频：22
❌ 失败：0
```

## 最佳实践

1. **定期清理缓存**: 避免缓存文件过大
2. **使用缓存**: 默认启用缓存，显著提升处理速度
3. **先预览后执行**: 大规模处理前先用 `--dry-run` 模式（旧版本支持）
4. **备份 MD 文件**: 重要文件操作前先备份
5. **分流处理**: 大量文件分批处理，避免单一任务运行过久

## 相关项目

- [Telegraph-Image GitHub](https://github.com/cf-pages/Telegraph-Image)
- [Cloudflare Pages](https://pages.cloudflare.com/)
- [Telegram Bot API](https://core.telegram.org/bots/api)

## 更新日志

- **2026-05-30**: 初始版本
  - 基础上传功能
  - 批量处理 MD 文件
  - 缓存机制
  - 视频缩略图识别
  - 自动去重