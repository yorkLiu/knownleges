#!/usr/bin/env python3
"""
X/Twitter 推文爬虫（增强版 v2）
- 按年分文件存储，避免单文件过大
- 智能去重，只追加新推文
- 详细统计报告
- 最新推文在最上面
- 支持时区配置
"""

import feedparser
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from html.parser import HTMLParser
import urllib.request
import urllib.error
import time
import socket

# Set default socket timeout for all HTTP requests
socket.setdefaulttimeout(30)

# ============ 配置读取 ============
SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"

# 加载配置
with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = json.load(f)

TARGET_USERS = config["target_users"]
OUTPUT_DIR = Path(config["output_dir"])
RSS_BASE_URL = config.get("rss_base_url", "https://nitter.net")
MAX_TWEETS = config.get("max_tweets_per_user", 20)
TIMEZONE_STR = config.get("timezone", "GMT+08:00")
TIMEZONE_OFFSET = config.get("timezone_offset", 8)  # 默认东八区

OUTPUT_DIR.mkdir(exist_ok=True)

# ============ 图片存储配置 ============
# 图片保存到 docs/public/images/（与 VitePress publicDir 对齐）
# 使用相对路径，基于项目根目录
IMAGES_DIR = Path(__file__).parents[2] / "docs/public/images"
IMAGES_DIR.mkdir(exist_ok=True, parents=True)

# ============ 统计报告配置 ============
STATS_DIR = SCRIPT_DIR.parent / "stats"
STATS_DIR.mkdir(exist_ok=True)

# ============ Telegraph 图床集成 ============
# 下载图片后自动上传到 Telegraph 图床
TELEGRAPH_ENABLED = True  # 设为 False 可禁用 Telegraph 上传
TELEGRAPH_BASE_URL = "https://telegraph-image-fork.pages.dev"
TELEGRAPH_UPLOAD_URL = f"{TELEGRAPH_BASE_URL}/upload"
TELEGRAPH_CACHE_FILE = SCRIPT_DIR / "telegraph_cache.json"

TODAY = datetime.now().strftime("%Y%m%d")
STATS_FILE = STATS_DIR / f"fetch_stats_{TODAY}.md"

# ============ 工具函数 ============

class ImageExtractor(HTMLParser):
    """从 HTML 中提取图片链接"""
    def __init__(self):
        super().__init__()
        self.images = []
        
    def handle_starttag(self, tag, attrs):
        if tag == 'img':
            attrs_dict = dict(attrs)
            if 'src' in attrs_dict:
                self.images.append(attrs_dict['src'])

def _load_telegraph_cache():
    """加载 Telegraph 上传缓存"""
    if TELEGRAPH_CACHE_FILE.exists():
        try:
            with open(TELEGRAPH_CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def _save_telegraph_cache(cache):
    """保存 Telegraph 上传缓存"""
    with open(TELEGRAPH_CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def _is_video_thumbnail(image_path):
    """判断是否是视频缩略图"""
    image_path_str = str(image_path).lower()
    video_keywords = ['video', 'amplify_video_thumb', 'ext_tw_video_thumb']
    return any(keyword in image_path_str for keyword in video_keywords)

def _upload_to_telegraph(image_path, verbose=True):
    """
    上传图片到 Telegraph 图床（带缓存）
    
    Args:
        image_path: 本地图片文件绝对路径
        verbose: 是否打印详细日志
    
    Returns:
        成功返回完整的图床 URL，失败返回 None
    """
    import subprocess
    
    image_path = Path(image_path).expanduser().absolute()
    
    if not image_path.exists():
        if verbose:
            print(f"  ❌ 文件不存在：{image_path}")
        return None
    
    if not image_path.is_file():
        if verbose:
            print(f"  ❌ 不是文件：{image_path}")
        return None
    
    # 检查文件扩展名（仅图片）
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
    if image_path.suffix.lower() not in allowed_extensions:
        if verbose:
            print(f"  ⚠️  不是图片文件，跳过：{image_path.suffix}")
        return None
    
    # 跳过视频缩略图
    if _is_video_thumbnail(image_path):
        if verbose:
            print(f"  ⏭️  跳过视频缩略图：{image_path.name}")
        return None
    
    # 检查缓存
    cache = _load_telegraph_cache()
    cache_key = str(image_path)
    if cache_key in cache:
        if verbose:
            print(f"  ♻️  使用缓存：{image_path.name} → {cache[cache_key][:60]}...")
        return cache[cache_key]
    
    if verbose:
        print(f"  📤 正在上传：{image_path.name}...")
    
    try:
        # 使用 curl 上传
        result = subprocess.run([
            'curl', '-s', '-X', 'POST',
            TELEGRAPH_UPLOAD_URL,
            '-F', f'file=@{image_path}',
            '-H', 'User-Agent: Mozilla/5.0',
            '-w', '\n%{http_code}'
        ], capture_output=True, text=True, timeout=60)
        
        # 解析响应
        lines = result.stdout.strip().split('\n')
        http_code = lines[-1] if lines else '0'
        body = '\n'.join(lines[:-1]) if len(lines) > 1 else ''
        
        if http_code != '200':
            if verbose:
                print(f"  ❌ 上传失败，HTTP 状态码：{http_code}")
            return None
        
        # 解析 JSON 响应
        try:
            response_data = json.loads(body)
            if isinstance(response_data, list) and len(response_data) > 0:
                src_path = response_data[0].get('src', '')
                if src_path:
                    full_url = f"{TELEGRAPH_BASE_URL}{src_path}"
                    if verbose:
                        print(f"  ✅ 上传成功：{full_url}")
                    # 保存到缓存
                    cache[cache_key] = full_url
                    _save_telegraph_cache(cache)
                    return full_url
        except json.JSONDecodeError as e:
            if verbose:
                print(f"  ❌ JSON 解析失败：{e}")
            if verbose:
                print(f"     原始响应：{body[:200]}")
        
        return None
        
    except subprocess.TimeoutExpired:
        if verbose:
            print(f"  ❌ 上传超时")
        return None
    except Exception as e:
        if verbose:
            print(f"  ❌ 上传异常：{e}")
        return None

def download_image(image_url, username, retry=5):
    """
    下载图片到本地，并上传到 Telegraph 图床
    Returns:
        tuple: (success: bool, url_or_path: str)
            - 成功（Telegraph）: (True, "https://telegraph-image-fork.pages.dev/file/xxx.jpg")
            - 成功（本地）: (True, "/images/username/image_id.jpg")
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
            # 优先返回 Telegraph URL（如果已缓存）
            if TELEGRAPH_ENABLED:
                telegraph_url = _upload_to_telegraph(local_path, verbose=False)
                if telegraph_url:
                    return (True, telegraph_url)
            # 否则返回本地路径
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
                    # 下载成功后上传到 Telegraph
                    if TELEGRAPH_ENABLED:
                        telegraph_url = _upload_to_telegraph(local_path, verbose=False)
                        if telegraph_url:
                            return (True, telegraph_url)
                    # 上传失败或未启用，返回本地路径
                    print(f"    ⚠️  Telegraph 上传失败，使用本地路径")
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


def format_time(dt):
    """将 datetime 对象格式化为字符串"""
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def parse_time_with_timezone(time_str):
    """解析时间字符串，返回带时区信息的 datetime"""
    # Nitter 返回的格式：Mon, 25 May 2026 07:04:59 GMT
    try:
        # 手动处理 "GMT" 以确保兼容性（某些环境下 %Z 解析失败）
        if time_str.endswith(" GMT"):
            time_str_clean = time_str[:-4]  # 去掉 " GMT"
            dt = datetime.strptime(time_str_clean, "%a, %d %b %Y %H:%M:%S")
        elif time_str.endswith(" UTC"):
            time_str_clean = time_str[:-4]
            dt = datetime.strptime(time_str_clean, "%a, %d %b %Y %H:%M:%S")
        else:
            # 尝试直接解析（兼容其他格式）
            dt = datetime.strptime(time_str, "%a, %d %b %Y %H:%M:%S %Z")
        
        # 转换为指定时区 (假设解析出的 dt 是 UTC)
        dt_local = dt + timedelta(hours=TIMEZONE_OFFSET)
        return dt_local
    except Exception as e:
        print(f"    ⚠️ 时间解析失败：{time_str} ({e})")
        return datetime.now()

def fetch_user_tweets(username):
    """从 Nitter RSS 获取用户推文"""
    rss_url = f"{RSS_BASE_URL}/{username}/rss"
    
    try:
        feed = feedparser.parse(rss_url)
        entries = feed.entries
        
        if not entries:
            return []
        
        processed_tweets = []
        
        for entry in entries:
            title = entry.get("title", "")
            link = entry.get("link", "")
            published = entry.get("published", "")
            summary = entry.get("summary", "")
            
            # 解析并转换时间
            pub_time = parse_time_with_timezone(published)
            time_str = format_time(pub_time)
            
            # 提取图片链接
            images = []
            if summary:
                extractor = ImageExtractor()
                extractor.feed(summary)
                images = extractor.images
            
            processed_tweets.append({
                "content": title,
                "link": link,
                "time": time_str,
                "time_obj": pub_time,  # 用于排序
                "user": username,
                "images": images
            })
        
        return processed_tweets
    except Exception as e:
        print(f" ❌ 获取失败：{e}")
        return []

def get_existing_tweet_ids(username):
    """获取已存在的推文 ID 列表（从每日文件）"""
    user_dir = OUTPUT_DIR / username
    if not user_dir.exists():
        return set()
    
    existing_ids = set()
    try:
        # 读取所有每日文件
        for daily_file in user_dir.glob("*.md"):
            if daily_file.name == "meta.json":
                continue
            try:
                content = daily_file.read_text(encoding="utf-8")
                pattern = r'status/(\d+)'
                matches = re.findall(pattern, content)
                existing_ids.update(matches)
            except:
                pass
    except Exception:
        pass
    
    return existing_ids

def get_tweet_id(link):
    """从推文链接中提取推文 ID"""
    match = re.search(r'status/(\d+)', link)
    if match:
        return match.group(1)
    return None

def parse_existing_tweets(content, username):
    """
    解析现有 Markdown 文件中的推文
    
    Returns: list of tweet dicts with keys: time, time_obj, content, link, images, local_images, failed_images
    """
    tweets = []
    
# 使用正则表达式按推文标题分割（## 2026-05-27 00:03:13 或带 GMT 后缀）
    # 改进：使用前瞻断言，确保匹配的是时间戳行而非内容中的 ## 标题
    # 时间戳格式：## YYYY-mm-dd HH:MM:SS [GMT[+-]X:00]
    tweet_pattern = r'(?=^## \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\sGMT[+-]\d{2}:\d{2})?(?:\s|$))'
    sections = re.split(tweet_pattern, content, flags=re.MULTILINE)
    
    for section in sections:
        section = section.strip()
        if not section:
            continue
        # 从 section 提取时间戳行
        time_match = re.match(r'^## (.+?)\s*$', section, re.MULTILINE)
        if not time_match:
            continue
        time_str = time_match.group(1).strip()
        
        # 解析时间对象（用于排序）
        try:
            # 移除 GMT 时区信息
            time_clean = re.sub(r'\s*GMT[+-]\d{2}:\d{2}', '', time_str)
            time_obj = datetime.strptime(time_clean, "%Y-%m-%d %H:%M:%S")
        except:
            time_obj = datetime.now()
        
        tweet_body = section
        # 提取内容
        content_match = re.search(r'\*\*内容\*\*:\s*\n\n(.+?)(?=\n\n\*\*图片\*\*:|$)', tweet_body, re.DOTALL)
        tweet_content = content_match.group(1).strip() if content_match else ""
        
        # 提取链接
        link_match = re.search(r'\[查看原文\]\(([^)]+)\)', tweet_body)
        link = link_match.group(1) if link_match else ""
        
# 提取本地图片路径（兼容 src=""path 和 src="path" 和 markdown 格式）
        local_images = []
        seen_paths = set()
        img_idx = 0

        # 1. HTML img 标签：src=""path 和 src="path" 两种格式
        img_pattern = r'src=""\s*([^\s"]+)|src="([^"]+)"'
        for p1, p2 in re.findall(img_pattern, tweet_body):
            img_path = (p1 or p2)
            if img_path.startswith('/images/') and img_path not in seen_paths:
                seen_paths.add(img_path)
                img_idx += 1
                local_images.append((img_idx, img_path))

        # 2. Markdown 图片：![alt](path)
        md_img_pattern = r'!\[[^\]]*\]\(([^)]+)\)'
        for md_path in re.findall(md_img_pattern, tweet_body):
            # 标准化路径：../public/images/ → /images/
            normalized = md_path.replace('../public', '')
            if normalized.startswith('/images/') and normalized not in seen_paths:
                seen_paths.add(normalized)
                img_idx += 1
                local_images.append((img_idx, normalized))
        
        # 提取远程图片 URL
        failed_images = []
        remote_pattern = r'src="https?://([^"]+)"'
        remote_matches = re.findall(remote_pattern, tweet_body)
        for i, img_url in enumerate(remote_matches, 1):
            failed_images.append((i, f'https://{img_url}'))
        
        tweets.append({
            'time': time_str,
            'time_obj': time_obj,
            'content': tweet_content,
            'link': link,
            'local_images': local_images,
            'failed_images': failed_images,
            'user': username,
            'tags': [],  # tags 由调用方根据时间计算
        })
    
    return tweets


def save_to_markdown(username, desc, tweets, stats):
    """保存推文到每日 Markdown 文件
    
    核心逻辑：
    1. 按日期分组新推文
    2. 对每个日期，读取现有每日文件（如果存在）
    3. 合并新推文和旧推文（去重）
    4. 写入每日文件
    """
    user_dir = OUTPUT_DIR / username
    user_dir.mkdir(exist_ok=True, parents=True)
    
    # 去重：只保留不重复的新推文
    existing_ids = get_existing_tweet_ids(username)
    new_tweets = []
    for tweet in tweets:
        tweet_id = get_tweet_id(tweet['link'])
        if tweet_id and tweet_id not in existing_ids:
            new_tweets.append(tweet)
            existing_ids.add(tweet_id)
    
    stats['fetched'] += len(tweets)
    stats['new'] += len(new_tweets)
    stats['duplicates'] += (len(tweets) - len(new_tweets))
    
    if not new_tweets:
        return user_dir, False, 0
    
    # 下载新推文图片
    downloaded_imgs = 0
    for tweet in new_tweets:
        if tweet['images']:
            tweet['local_images'] = []
            tweet['failed_images'] = []
            for idx, img_url in enumerate(tweet['images'], 1):
                success, path = download_image(img_url, username)
                if success:
                    tweet['local_images'].append((idx, path))
                    downloaded_imgs += 1
                else:
                    tweet['failed_images'].append((idx, path))
    
    # 按日期分组
    tweets_by_date = {}
    for tweet in new_tweets:
        date_str = tweet['time_obj'].strftime('%Y-%m-%d')
        if date_str not in tweets_by_date:
            tweets_by_date[date_str] = []
        tweets_by_date[date_str].append(tweet)
    
    # 计算标签
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    this_week_start = today - timedelta(days=today.weekday())
    
    def get_tweet_tags(tweet_time_obj):
        tags = []
        if tweet_time_obj >= today:
            tags.append("今日关注")
        elif tweet_time_obj >= this_week_start:
            tags.append("本周精选")
        return tags
    
    # 保存到每日文件
    for date_str, day_tweets in tweets_by_date.items():
        daily_file = user_dir / f"{date_str}.md"
        
        # 读取现有推文（如果文件存在）
        existing_tweets = []
        if daily_file.exists():
            try:
                content = daily_file.read_text(encoding="utf-8")
                existing_tweets = parse_existing_tweets(content, username)
            except Exception as e:
                print(f"    ⚠️ 解析现有推文失败：{e}")
        
        # 合并新推文和旧推文，并按链接去重
        seen_links = set()
        all_tweets_unique = []
        for t in day_tweets + existing_tweets:
            if t['link'] and t['link'] not in seen_links:
                seen_links.add(t['link'])
                all_tweets_unique.append(t)
        
        # 按时间倒序排序
        all_tweets_sorted = sorted(all_tweets_unique, key=lambda x: x['time_obj'], reverse=True)
        
        # 写入文件
        with open(daily_file, "w", encoding="utf-8") as f:
            for tweet in all_tweets_sorted:
                tags = get_tweet_tags(tweet['time_obj'])
                
                f.write(f"## {tweet['time']}\n\n")
                
                # 写入标签
                if tags:
                    tags_str = "  ".join([
                        f'<a href="/tags.html?tag={tag}" class="tag-badge tag-{tag}">🏷️ {tag}</a>'
                        for tag in tags
                    ])
                    f.write(f"{tags_str}\n\n")
                
                f.write(f"**内容**:\n\n{tweet['content']}\n\n")
                
                # 写入本地图片
                for idx, local_path in tweet.get('local_images', []):
                    f.write(f'<img src="{local_path}" alt="图片 {idx}" style="max-width:100%;border-radius:8px;margin:8px 0;">\n\n')
                
                # 写入远程图片
                for idx, remote_url in tweet.get('failed_images', []):
                    f.write(f'<img src="{remote_url}" alt="图片 {idx}" style="max-width:100%;border-radius:8px;margin:8px 0;">\n\n')
                
                f.write(f"[查看原文]({tweet['link']})\n\n")
                f.write("---\n\n")
    
    # 更新 meta.json
    meta_file = user_dir / "meta.json"
    meta = {
        "username": username,
        "description": desc,
        "year": datetime.now().year,
        "last_updated": datetime.now().strftime(f"%Y-%m-%d %H:%M:%S {TIMEZONE_STR}"),
        "total_tweets": len(existing_ids)
    }
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    
    return user_dir, True, downloaded_imgs

def save_stats_report(all_stats):
    """保存统计报告"""
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        f.write(f"# X/Twitter 推文抓取统计报告\n\n")
        f.write(f"**日期**: {datetime.now().strftime(f'%Y-%m-%d %H:%M:%S {TIMEZONE_STR}')}**\n\n")
        f.write(f"## 总体统计\n\n")
        f.write(f"- **总抓取用户数**: {all_stats['total_users']}\n")
        f.write(f"- **总获取推文数**: {all_stats['fetched']} 条\n")
        f.write(f"- **新增推文数**: {all_stats['new']} 条\n")
        f.write(f"- **重复推文数**: {all_stats['duplicates']} 条\n")
        dup_rate = (all_stats['duplicates'] / all_stats['fetched'] * 100) if all_stats['fetched'] > 0 else 0
        f.write(f"- **去重率**: {dup_rate:.1f}%\n\n")
        f.write(f"## 用户详情\n\n")
        f.write(f"| 用户 | 获取数 | 新增数 | 重复数 |\n")
        f.write(f"|------|--------|--------|--------|\n")
        for username, data in all_stats['users'].items():
            f.write(f"| @{username} | {data['fetched']} | {data['new']} | {data['duplicates']} |\n")
        f.write(f"\n## 说明\n\n")
        f.write(f"- 推文按年份分文件存储，避免单文件过大\n")
        f.write(f"- 自动去重，只追加新推文\n")
        f.write(f"- 图片自动下载到本地 `images/` 目录\n")
        f.write(f"- 时间显示时区：{TIMEZONE_STR}\n")




def build_yearly_summary():
    """合并每日文件生成年度汇总文件，更新 index.md"""
    print("\n  🏗️ 正在构建年度汇总文件...")
    docs_x_post_dir = Path(__file__).parents[2] / "docs/x_post_data"
    docs_x_post_dir.mkdir(exist_ok=True)
    index_file = docs_x_post_dir / "index.md"
    
    # 准备新的表格行
    table_rows = []
    import time
    
    for username, description in TARGET_USERS.items():
        user_dir = OUTPUT_DIR / username
        if not user_dir.exists():
            continue
        
        # 收集该用户当年的所有日报
        current_year = datetime.now().year
        daily_files = sorted([f for f in user_dir.glob("*.md") if f.name != "meta.json" and re.match(r"\d{4}-\d{2}-\d{2}", f.stem)], key=lambda x: x.name)
        
        if not daily_files:
            continue
        
        # 收集所有推文内容
        all_tweets = []
        for daily_file in daily_files:
            try:
                with open(daily_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    # 按推文分割（每个推文以 "## 时间" 开始，以 "---" 结束）
                    sections = content.split("---\n\n")
                    for section in sections:
                        if section.strip().startswith("## "):
                            all_tweets.append(section.strip())
            except Exception as e:
                print(f"    ⚠️ 读取 {daily_file.name} 失败：{e}")
        
        if not all_tweets:
            continue
        
        # 构建年度汇总文件内容
        summary_file = docs_x_post_dir / f"{username}_{current_year}.md"
        with open(summary_file, "w", encoding="utf-8") as f:
            # YAML Frontmatter
            f.write(f"---\n")
            f.write(f"title: \"@{username} 推文存档\"\n")
            f.write(f"date: {current_year}-01-01\n")
            f.write(f"author: \"@{username}\"\n")
            f.write(f"tags: [\"{current_year}\"]\n")
            f.write(f"---\n\n")
            f.write(f"# @{username}\n\n")
            f.write(f"> 📊 推文存档 - 共 {len(all_tweets)} 条推文\n\n")
            f.write(f"---\n\n")
            
            # 写入推文（倒序：最新的在最前）
            for tweet_section in reversed(all_tweets):
                f.write(f"{tweet_section}\n\n---\n\n")
        
        # 更新表格行
        image_count = sum(t.count("<img") for t in all_tweets)
        has_today = any(time.time() - f.stat().st_mtime < 86400 for f in daily_files)
        today_flag = "✅" if has_today else " "
        
        table_rows.append(f"|| [@{username}](./{username}_{current_year}.md) | {len(all_tweets)} | {today_flag} | {image_count} | [查看](./{username}_{current_year}.md) |")
        print(f"    ✅ 已生成 {username}_{current_year}.md ({len(all_tweets)} 条)")

    # 更新 index.md
    if index_file.exists() and table_rows:
        with open(index_file, "r", encoding="utf-8") as f:
            index_content = f.read()
        
        # 替换表格内容
        header_end = index_content.find("|------|")
        if header_end != -1:
            footer_start = index_content.find("\n---", header_end + 10)
            if footer_start == -1:
                footer_start = len(index_content)
            
            new_index = index_content[:header_end+8] + "\n" + "\n".join(table_rows) + index_content[footer_start:]
            with open(index_file, "w", encoding="utf-8") as f:
                f.write(new_index)
            print(f"  ✅ 已更新 index.md")


def main():
    print("=" * 70)
    print("🚀 X/Twitter 推文爬虫 (增强版 v2)")
    print("=" * 70)
    print(f"📂 输出目录：{OUTPUT_DIR}")
    print(f"🕐 时区设置：{TIMEZONE_STR}")
    print()
    
    all_stats = {
        'total_users': 0,
        'fetched': 0,
        'new': 0,
        'duplicates': 0,
        'users': {}
    }
    
    for username, description in TARGET_USERS.items():
        print(f"📥 正在获取 @{username} ({description})...", end=" ")
        tweets = fetch_user_tweets(username)
        
        if tweets:
            print(f"✅ {len(tweets)} 条推文")
            
            img_count = sum(len(t['images']) for t in tweets)
            user_stats = {'fetched': 0, 'new': 0, 'duplicates': 0}
            user_dir, has_new, downloaded_imgs = save_to_markdown(username, description, tweets, user_stats)
            
            if has_new:
                print(f" 💾 已保存到：{user_dir.name} (新增 {user_stats['new']} 条)")
                if downloaded_imgs > 0:
                    print(f" 🖼️ 实际下载 {downloaded_imgs} 张图片")
            else:
                print(f" ⏭️ 无新推文，跳过写入")
            
            all_stats['total_users'] += 1
            all_stats['fetched'] += user_stats['fetched']
            all_stats['new'] += user_stats['new']
            all_stats['duplicates'] += user_stats['duplicates']
            all_stats['users'][username] = {
                'fetched': user_stats['fetched'],
                'new': user_stats['new'],
                'duplicates': user_stats['duplicates'],
            }
        else:
            print(f"⚠️ 无法获取\n")
    
    print("\n📋 正在生成统计报告...", end=" ")
    save_stats_report(all_stats)
    print(f"✅ {STATS_FILE.name}\n")

    print("=" * 70)
    print(f"✅ 完成！")
    print(f" 📊 成功同步：{all_stats['total_users']} 个用户")
    print(f" 📝 总获取推文：{all_stats['fetched']} 条")
    print(f" ✨ 新增推文：{all_stats['new']} 条")
    print(f" 🔄 重复推文：{all_stats['duplicates']} 条")
    print(f" 📁 图片目录：images/")
    print(f" 📊 统计报告：{STATS_FILE.name}")
    print(f" 🕐 时区：{TIMEZONE_STR}")
    print("=" * 70)
    build_yearly_summary()


if __name__ == "__main__":
    main()
