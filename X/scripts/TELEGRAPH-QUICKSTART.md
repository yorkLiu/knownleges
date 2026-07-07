# X/Twitter 推文图片 Telegraph 图床集成 - 完整指南

## 📋 项目概述

本项目已将 X/Twitter 推文爬虫与 Telegraph-Image 图床完全集成，实现：
- ✅ 自动图片上传
- ✅ 智能去重缓存
- ✅ 视频缩略图识别（自动跳过）
- ✅ 批量 MD 文件更新
- ✅ 稳定的 CDN 加速

**图床服务**: https://telegraph-image-fork.pages.dev

## 🚀 快速开始

### 1. 测试上传功能

```bash
cd /home/hermes/workspace/knownleges/X/scripts

# 测试上传单张图片
python upload_to_telegraph.py /path/to/test_image.png
```

### 2. 批量处理现有 MD 文件（预览模式）

```bash
# 使用集成脚本（带缓存）
python upload_images_integration.py --all -q
```

### 3. 正式执行

```bash
# 处理所有 MD 文件
python upload_images_integration.py --all

# 带缓存统计
python upload_images_integration.py --all --no-cache
```

## 📁 文件结构

```
/home/hermes/workspace/knownleges/X/scripts/
├── upload_to_telegraph.py          # 基础上传工具
├── upload_images_integration.py    # 批量处理工具（推荐）
├── upload_images_to_telegraph.py   # 旧版本（保留兼容性）
├── telegraph_cache.json            # 上传缓存（自动生成）
├── TELEGRAPH-README.md             # 详细文档
├── TELEGRAPH-INTEGRATION-EXAMPLES.md  # 集成示例
└── TELEGRAPH-QUICKSTART.md         # 本文件

/home/hermes/workspace/knownleges/docs/public/images/
├── elonmusk/
│   ├── media_*.jpg                  # 本地图片（可删除）
│   └── amplify_video_thumb_*.jpg    # 视频缩略图（保留）
└── ...
```

## 🛠️ 使用场景

### 场景 1：处理现有推文

如果已有大量本地图片的 MD 文件：

```bash
cd /home/hermes/workspace/knownleges/X/scripts

# 1. 备份现有文件（可选但推荐）
cp -r /home/hermes/workspace/knownleges/docs/x_post_data/*.md /backup/

# 2. 批量处理（会自动使用缓存）
python upload_images_integration.py --all

# 3. 查看结果
cat telegraph_cache.json | python -c "import sys,json; d=json.load(sys.stdin); print(f'已缓存 {len(d)} 张图片')"
```

### 场景 2：爬虫自动集成

修改 `fetch_x_users.py`，在 `download_image()` 函数中：

```python
from upload_to_telegraph import upload_to_telegraph

def download_image(image_url, username, retry=5):
    # ... 原有下载逻辑 ...
    
    # 下载成功后添加到上传
    if success:
        telegraph_url = upload_to_telegraph(str(local_path), verbose=False)
        if telegraph_url:
            return (True, telegraph_url)  # 优先返回图床 URL
        return (True, f"/images/{username}/{image_id}")  # 失败返回本地路径
    
    return (False, image_url)
```

### 场景 3：定期维护

```bash
# 每周运行一次，处理新图片
0 2 * * 0 cd /home/hermes/workspace/knownleges/X/scripts && python upload_images_integration.py --all -q

# 每月清理一次缓存（删除不存在的文件）
# 手动运行清理脚本
```

## 📊 命令详解

### upload_to_telegraph.py

| 参数 | 说明 | 示例 |
|------|------|------|
| 无 | 显示帮助 | `python upload_to_telegraph.py` |
| `<文件路径>` | 上传单张图片 | `python upload_to_telegraph.py image.jpg` |
| `--md <MD> <图片> [描述]` | 生成 Markdown 格式 | `python upload_to_telegraph.py --md post.md img.jpg "描述"` |

### upload_images_integration.py

| 参数 | 说明 | 示例 |
|------|------|------|
| `--all` | 处理所有 MD 文件 | `python upload_images_integration.py --all` |
| `<file1> <file2>` | 处理指定文件 | `python upload_images_integration.py a.md b.md` |
| `--no-cache` | 不使用缓存 | `python upload_images_integration.py --all --no-cache` |
| `-q, --quiet` | 静默模式 | `python upload_images_integration.py --all -q` |
| `--help` | 显示帮助 | `python upload_images_integration.py --help` |

## 📈 输出示例

### 成功输出

```
🚀 开始处理 10 个文件
📁 图床地址：https://telegraph-image-fork.pages.dev
📂 图片目录：/home/hermes/workspace/knownleges/docs/public/images
💾 缓存文件：/home/hermes/workspace/knownleges/X/scripts/telegraph_cache.json

📄 处理文件：elonmusk_2026.md
  📊 找到 52 张图片
  📤 正在上传：media_HJg1dugWIAQfkEU.jpg...
  ✅ 上传成功：https://telegraph-image-fork.pages.dev/file/xxx.jpg
  ⏭️  跳过视频缩略图：amplify_video_thumb_*.jpg
  ♻️  使用缓存：media_HJgKjTKagAA2l8c.png → https://...

============================================================
📊 汇总统计
============================================================
总图片数：520
♻️  从缓存：36
✅ 新上传：16
⏭️  跳过视频：22
❌ 失败：0
```

## ⚠️ 注意事项

### 视频处理

系统会自动识别并跳过视频缩略图，识别规则：
- 文件名包含 `video`, `amplify_video_thumb`, `ext_tw_video_thumb`
- 这些图片会继续使用本地路径或 nitter 链接

### 缓存管理

缓存文件会自动生成和更新：

```bash
# 查看缓存状态
ls -lh telegraph_cache.json
python -c "import json; print(f'已缓存 {len(json.load(open(\"telegraph_cache.json\")))} 张图片')"

# 清除缓存（强制重新上传）
rm telegraph_cache.json
python upload_images_integration.py --all --no-cache

# 清理无效缓存（文件已删除的条目）
python << 'EOF'
import json
from pathlib import Path

cache_file = 'telegraph_cache.json'
cache = json.load(open(cache_file))

# 检查文件是否存在
valid_cache = {
    path: url for path, url in cache.items()
    if Path(path).exists()
}

if len(valid_cache) < len(cache):
    print(f"清理 {len(cache) - len(valid_cache)} 个无效缓存")
    json.dump(valid_cache, open(cache_file, 'w'), indent=2, ensure_ascii=False)
else:
    print("所有缓存都有效")
EOF
```

### 故障排除

**问题 1：上传失败**
```bash
# 检查网络连通性
curl -I https://telegraph-image-fork.pages.dev

# 检查文件权限
ls -la /home/hermes/workspace/knownleges/docs/public/images/

# 手动测试上传
python upload_to_telegraph.py /path/to/image.jpg
```

**问题 2：MD 文件替换失败**
```bash
# 检查 MD 文件中的图片格式
grep -oP '<img src=[^>]+' docs/x_post_data/elonmusk_2026.md | head

# 如果是其他格式（如 Markdown 语法），需要调整正则表达式
```

**问题 3：缓存文件损坏**
```bash
# 重新生成缓存
rm telegraph_cache.json
python upload_images_integration.py --all --no-cache -q
```

## 📖 集成文档

详细的集成说明请参考：

1. **[TELEGRAPH-README.md](TELEGRAPH-README.md)** - 完整使用说明
2. **[TELEGRAPH-INTEGRATION-EXAMPLES.md](TELEGRAPH-INTEGRATION-EXAMPLES.md)** - 代码集成示例
3. **upload_to_telegraph.py** - 基础上传工具源码

## 🔄 更新日志

- **2026-05-30 v1.0** - 初始版本
  - 基础上传功能
  - 批量处理 MD 文件
  - 缓存机制
  - 视频缩略图识别
  - 自动去重

## 💡 最佳实践

1. **先测试后批量**: 大规模处理前先测试单个文件
2. **使用缓存**: 默认启用缓存，避免重复上传
3. **定期备份**: 重要 MD 文件操作前先备份
4. **监控统计**: 查看上传统计，确保成功率
5. **分流处理**: 大量文件分批处理

## 📞 技术支持

如遇问题，请检查：

1. 网络连接
2. 文件权限
3. 缓存状态
4. 日志输出

---

**图床服务**: https://telegraph-image-fork.pages.dev  
**项目地址**: /home/hermes/workspace/knownleges  
**文档版本**: 2026-05-30