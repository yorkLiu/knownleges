# Telegraph 图床集成示例

## 如何将爬虫下载的图片自动上传到 Telegraph 图床

### 修改 fetch_x_users.py

在 `download_image()` 函数中添加上传逻辑：

```python
import sys
from pathlib import Path

# 在文件开头添加导入
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
from upload_to_telegraph import upload_to_telegraph

# 修改 download_image 函数
def download_image(image_url, username, retry=5):
    """
    下载图片到本地，并上传到 Telegraph 图床
    返回 Telegraph 图床 URL（优先）或本地路径

    Returns:
        tuple: (success: bool, url_or_path: str)
            - 成功：(True, "https://telegraph-image-fork.pages.dev/file/xxx.jpg")
            - 失败：(False, "https://nitter.net/pic/media_xxx.jpg")
    """
    try:
        image_id = image_url.split('/')[-1].replace('%2F', '_')
        image_id = ''.join(c for c in image_id if c.isalnum() or c in '._-')
        if not image_id:
            return (False, image_url)

        user_images_dir = IMAGES_DIR / username
        user_images_dir.mkdir(exist_ok=True)
        local_path = user_images_dir / image_id

        # 检查是否已存在
        if local_path.exists() and local_path.stat().st_size > 0:
            # 先尝试上传到 Telegraph
            telegraph_url = upload_to_telegraph(str(local_path), verbose=False)
            if telegraph_url:
                return (True, telegraph_url)
            # 上传失败，返回本地路径
            return (True, f"/images/{username}/{image_id}")

        # 下载图片
        for attempt in range(retry):
            try:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                req = urllib.request.Request(image_url, headers=headers)
                with urllib.request.urlopen(req, timeout=60) as response:
                    with open(local_path, 'wb') as img_file:
                        img_file.write(response.read())
                time.sleep(0.5)

                if local_path.exists() and local_path.stat().st_size > 0:
                    # 上传到 Telegraph
                    telegraph_url = upload_to_telegraph(str(local_path), verbose=False)
                    if telegraph_url:
                        return (True, telegraph_url)
                    # 上传失败，返回本地路径
                    return (True, f"/images/{username}/{image_id}")
                break
            except Exception as e:
                if attempt < retry - 1:
                    wait_time = 2 ** attempt
                    print(f"    下载失败，{wait_time}s 后重试 ({attempt+1}/{retry})...")
                    time.sleep(wait_time)
                else:
                    print(f"    下载失败（{retry}次重试已用完）: {image_url}")
                    return (False, image_url)

        # 所有重试失败
        return (False, image_url)
    except Exception as e:
        print(f"    下载异常：{e}")
        return (False, image_url)
```

### 修改 save_to_markdown 函数

更新 `save_to_markdown()` 函数以处理 Telegraph URL：

```python
def save_to_markdown(username, desc, tweets, year, stats):
    """
    保存推文到 Markdown 文件
    支持 Telegraph URL 和本地路径混合使用
    """
    output_file = OUTPUT_DIR / f"{username}_{year}.md"
    
    # ... 去重逻辑 ...
    
    # 下载新推文图片
    print(f"  📥 为 {len(new_tweets)} 条新推文下载图片...")
    for tweet in new_tweets:
        if tweet['images']:
            tweet['local_images'] = []
            tweet['failed_images'] = []
            for idx, img_url in enumerate(tweet['images'], 1):
                success, url_or_path = download_image(img_url, username)
                if success:
                    # 判断是 Telegraph URL 还是本地路径
                    if url_or_path.startswith('https://telegraph-image'):
                        # Telegraph URL 直接写入
                        tweet['local_images'].append((idx, url_or_path))
                    elif url_or_path.startswith('/images/'):
                        # 本地路径，保持不变
                        tweet['local_images'].append((idx, url_or_path))
                    else:
                        # 其他情况（可能是 nitter 备份链接）
                        tweet['failed_images'].append((idx, url_or_path))
                else:
                    tweet['failed_images'].append((idx, url_or_path))
    
    # ... 写入文件逻辑 ...
    
    # 写入图片时，根据路径类型选择标签格式
    for idx, img_src in tweet.get('local_images', []):
        if img_src.startswith('http'):
            # Telegraph URL
            f.write(f'<img src="{img_src}" alt="图片 {idx}" style="max-width:100%;border-radius:8px;margin:8px 0;">\\n\\n')
        else:
            # 本地路径
            f.write(f'<img src="{img_src}" alt="图片 {idx}" style="max-width:100%;border-radius:8px;margin:8px 0;">\\n\\n')
    
    # ... 其余逻辑 ...
```

## 使用流程

### 方案 A：完全使用 Telegraph 图床（推荐）

1. 修改 `fetch_x_users.py` 如上所示
2. 配置缓存避免重复上传
3. 爬虫运行时自动上传所有图片到 Telegraph
4. MD 文件中直接使用 Telegraph URL

**优点**:
- 无需本地图片存储
- 所有图片都有稳定 URL
- 自动 CDN 加速

**缺点**:
- 依赖 Telegraph 服务可用性
- 首次上传需要时间

### 方案 B：混合模式（稳定优先）

1. 优先使用 Telegraph 图床
2. 上传失败时使用本地路径作为后备
3. 定期批量上传本地图片到 Telegraph

**优点**:
- 更高的可靠性
- 不依赖单一服务

**缺点**:
- 需要同时管理本地和图床

### 方案 C：后处理模式

1. 爬虫正常运行，使用本地存储
2. 定期运行 `upload_images_integration.py --all`
3. 批量将本地图片上传到 Telegraph 并更新 MD 文件

**优点**:
- 爬虫运行更快
- 可以批量处理，优化上传效率

**缺点**:
- 需要额外的后处理步骤

## 配置优化

### 调整超时时间

如果上传速度较慢，可以增加超时：

```python
result = subprocess.run([
    'curl', '-s', '-X', 'POST',
    UPLOAD_URL,
    '-F', f'file=@{image_path}',
    '-H', 'User-Agent: Mozilla/5.0',
    '-w', '\\n%{http_code}'
], capture_output=True, text=True, timeout=120)  # 增加超时到 120 秒
```

### 添加重试逻辑

```python
def upload_to_telegraph_with_retry(image_path, max_retries=3):
    for attempt in range(max_retries):
        url = upload_to_telegraph(image_path)
        if url:
            return url
        print(f"  上传失败，{attempt+1}/{max_retries}，重试中...")
        time.sleep(2 ** attempt)
    return None
```

### 并发控制

Telegram 可能有速率限制，建议串行上传或限制并发数：

```python
from concurrent.futures import ThreadPoolExecutor

# 限制最大并发数为 5
with ThreadPoolExecutor(max_workers=5) as executor:
    results = list(executor.map(upload_to_telegraph, image_paths))
```

## 监控和维护

### 查看上传统计

```bash
# 查看缓存文件大小
ls -lh /home/hermes/workspace/knownleges/X/scripts/telegraph_cache.json

# 查看缓存内容（前 20 行）
head -20 /home/hermes/workspace/knownleges/X/scripts/telegraph_cache.json

# 统计已上传图片数量
python -c "import json; cache=json.load(open('telegraph_cache.json')); print(f'已缓存 {len(cache)} 张图片')"
```

### 清理无效缓存

```bash
# 检查缓存中的文件是否仍然存在
python << 'EOF'
import json
from pathlib import Path

cache = json.load(open('telegraph_cache.json'))
missing = []

for local_path in cache.keys():
    if not Path(local_path).exists():
        missing.append(local_path)

if missing:
    print(f"发现 {len(missing)} 个文件已删除:")
    for path in missing[:10]:
        print(f"  - {path}")
else:
    print("所有缓存文件都存在")
EOF
```

## 故障恢复

### 批量重传失败图片

```bash
# 创建失败图片列表
python << 'EOF'
import re

md_file = 'docs/x_post_data/elonmusk_2026.md'
with open(md_file, 'r') as f:
    content = f.read()

# 找出所有仍在使用 nitter 链接的图片
img_pattern = r'<img\s+src="(https://nitter\.net[^"]+)"'
matches = re.findall(img_pattern, content)

if matches:
    print(f"发现 {len(matches)} 张图片仍在使用 nitter 链接:")
    for url in matches[:10]:
        print(f"  - {url}")
else:
    print("所有图片都已上传到 Telegraph")
EOF
```

## 性能调优

### 批量上传优化

```python
def batch_upload_images(image_paths, batch_size=10):
    """批量上传图片，每批后暂停避免速率限制"""
    cache = load_cache()
    results = {}
    
    for i, image_path in enumerate(image_paths, 1):
        if str(image_path) in cache:
            results[image_path] = cache[str(image_path)]
            continue
        
        url = upload_to_telegraph(image_path)
        if url:
            cache[str(image_path)] = url
            save_cache(cache)
            results[image_path] = url
        
        # 每 10 张图片暂停 2 秒
        if i % batch_size == 0:
            print(f"  已处理 {i}/{len(image_paths)} 张，暂停 2 秒...")
            time.sleep(2)
    
    return results
```

## 总结

Telegraph-Image 图床为 X/Twitter 推文图片存储提供了免费、稳定的解决方案。根据你的需求选择合适的集成方案：

- **快速启动**: 方案 A（完全使用 Telegraph）
- **稳定优先**: 方案 B（混合模式）
- **现有项目**: 方案 C（后处理模式）

无论选择哪种方案，都能显著提升图片加载速度和可靠性！