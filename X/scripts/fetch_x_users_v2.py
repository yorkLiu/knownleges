#!/usr/bin/env python3
"""
X/Twitter 推文抓取工具（支持多种数据源）

支持:
  - nitter (默认)
  - twitter-api (通过 Bearer Token)
  - rsshub (自建/公共 RSSHub 实例)

配置方式：修改 config.json 中的 provider 及相关字段即可切换。
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

# ============ 配置读取 ============
SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"

with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = json.load(f)

TARGET_USERS = config["target_users"]
OUTPUT_DIR = Path(config["output_dir"])

# === 数据源配置 (新增) ===
PROVIDER = config.get("provider", "nitter")  # nitter 或 rsshub
RSS_BASE_URL = config.get("rss_base_url", "https://nitter.net")
MAX_TWEETS = config.get("max_tweets_per_user", 20)
TIMEZONE_STR = config.get("timezone", "GMT+08:00")
TIMEZONE_OFFSET = config.get("timezone_offset", 8)

OUTPUT_DIR.mkdir(exist_ok=True)

# ============ 图片存储配置 ============
IMAGES_DIR = Path(__file__).parents[2] / "docs/public/images"
IMAGES_DIR.mkdir(exist_ok=True, parents=True)

# ============ 统计报告配置 ============
STATS_DIR = SCRIPT_DIR.parent / "stats"
STATS_DIR.mkdir(exist_ok=True)

# ============ Telegraph 图床集成 ============
TELEGRAPH_ENABLED = True
TELEGRAPH_BASE_URL = "https://telegraph-image-fork.pages.dev"
TELEGRAPH_UPLOAD_URL = f"{TELEGRAPH_BASE_URL}/upload"
TELEGRAPH_CACHE_FILE = SCRIPT_DIR / "telegraph_cache.json"

TODAY = datetime.now().strftime("%Y%m%d")
STATS_FILE = STATS_DIR / f"fetch_stats_{TODAY}.md"

# ============ 工具函数 ============

class ImageExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []

    def handle_starttag(self, tag, attrs):
        if tag == 'img':
            attrs_dict = dict(attrs)
            if 'src' in attrs_dict:
                self.images.append(attrs_dict['src'])

def _load_telegraph_cache():
    if TELEGRAPH_CACHE_FILE.exists():
        try:
            with open(TELEGRAPH_CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def _save_telegraph_cache(cache):
    with open(TELEGRAPH_CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def _is_video_thumbnail(image_path):
    image_path_str = str(image_path).lower()
    video_keywords = ['video', 'amplify_video_thumb', 'ext_tw_video_thumb']
    return any(keyword in image_path_str for keyword in video_keywords)

def _upload_to_telegraph(image_path, verbose=True):
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
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
    if image_path.suffix.lower() not in allowed_extensions:
        if verbose:
            print(f"  ⏭️ 跳过非图片：{image_path.suffix}")
        return None
    cache = _load_telegraph_cache()
    image_name = image_path.name
    if image_name in cache:
        if verbose:
            print(f"  📦 缓存命中：{cache[image_name]}")
        return cache[image_name]
    try:
        result = subprocess.run(
            ["curl", "-s", "-F", f"file=@{image_path}", TELEGRAPH_UPLOAD_URL],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            try:
                resp = json.loads(result.stdout)
                if isinstance(resp, list) and len(resp) > 0:
                    url = resp[0].get("src", "")
                    if url:
                        full_url = f"{TELEGRAPH_BASE_URL}{url}" if url.startswith("/") else url
                        cache[image_name] = full_url
                        _save_telegraph_cache(cache)
                        if verbose:
                            print(f"  ✅ 上传成功：{full_url}")
                        return full_url
            except:
                pass
        if verbose:
            print(f"  ❌ 上传失败：{result.stderr}")
    except subprocess.TimeoutExpired:
        if verbose:
            print(f"  ⏰ 上传超时：{image_path}")
    except Exception as e:
        if verbose:
            print(f"  ❌ 上传异常：{e}")
    return None

def parse_time_with_timezone(pub_str):
    """
    解析带有 +0000 时区的时间字符串，转换为本地时间
    支持多种格式：
      - RSS 标准格式: "Sat, 04 Jan 2025 00:56:25 +0000"
      - 等.
    """
    import email.utils
    parsed = email.utils.parsedate_tz(pub_str)
    if parsed:
        utc_time = datetime(*parsed[:6]) - timedelta(seconds=parsed[-1] or 0)
        local_time = utc_time + timedelta(hours=TIMEZONE_OFFSET)
        return local_time
    try:
        utc_time = datetime.strptime(pub_str, "%a, %d %b %Y %H:%M:%S %z")
        local_time = utc_time + timedelta(hours=TIMEZONE_OFFSET)
        return local_time.replace(tzinfo=None)
    except:
        pass
    try:
        return datetime.strptime(pub_str, "%Y-%m-%dT%H:%M:%S.%fZ")
    except:
        pass
    try:
        return datetime.strptime(pub_str, "%Y-%m-%dT%H:%M:%SZ")
    except:
        pass
    return datetime.now()

def format_time(dt):
    """格式化时间为字符串"""
    return dt.strftime("%Y-%m-%d %H:%M:%S")

# ============ 数据源抓取函数 ============

def fetch_user_tweets_nitter(username):
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

            pub_time = parse_time_with_timezone(published)
            time_str = format_time(pub_time)

            images = []
            if summary:
                extractor = ImageExtractor()
                extractor.feed(summary)
                images = extractor.images

            processed_tweets.append({
                "content": title,
                "link": link,
                "time": time_str,
                "time_obj": pub_time,
                "user": username,
                "images": images
            })

        return processed_tweets
    except Exception as e:
        print(f" ❌ 获取失败：{e}")
        return []

def fetch_user_tweets_rsshub(username):
    """从 RSShub 获取用户推文"""
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

            pub_time = parse_time_with_timezone(published)
            time_str = format_time(pub_time)

            images = []
            if summary:
                extractor = ImageExtractor()
                extractor.feed(summary)
                images = extractor.images

            processed_tweets.append({
                "content": title,
                "link": link,
                "time": time_str,
                "time_obj": pub_time,
                "user": username,
                "images": images
            })

        return processed_tweets
    except Exception as e:
        print(f" ❌ 获取失败：{e}")
        return []

def fetch_user_tweets(username):
    """获取用户推文（自动选择数据源）"""
    if PROVIDER == "rsshub":
        return fetch_user_tweets_rsshub(username)
    return fetch_user_tweets_nitter(username)

# ============ 后续处理和原始代码保持一致 ============

# 读取剩余代码
# ... (保持与原始 fetch_x_users.py 一致)

def get_existing_tweet_ids(username):
    user_dir = OUTPUT_DIR / username
    if not user_dir.exists():
        return set()

    existing_ids = set()
    try:
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
    match = re.search(r'status/(\d+)', link)
    if match:
        return match.group(1)
    return None

def parse_existing_tweets(content, username):
    """解析现有 Markdown 文件中的推文"""
    import html
    tweets = []
    lines = content.split("\n")

    current_tweet = {}
    in_tweet = False

    for line in lines:
        # 匹配推文标题行: ### 2025-01-04 00:56:25
        tweet_header = re.match(r'^###\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', line)
        if tweet_header:
            if current_tweet and "content" in current_tweet:
                tweets.append(current_tweet)
            current_tweet = {"time": tweet_header.group(1), "images": [], "local_images": [], "failed_images": []}
            in_tweet = True
            continue

        if not in_tweet:
            continue

        # 匹配推文内容（> 内容）
        content_match = re.match(r'>\s*(.*)', line)
        if content_match and "content" not in current_tweet:
            current_tweet["content"] = content_match.group(1)
            continue

        # 匹配链接
        link_match = re.search(r'(https://x\.com/\w+/status/\d+)', line)
        if link_match and "link" not in current_tweet:
            current_tweet["link"] = link_match.group(1)
            continue

        # 匹配 Telegraph 图片
        img_match = re.match(r'!\[\]\((https://telegraph-image[^)]+)\)', line)
        if img_match:
            current_tweet.setdefault("images", []).append(img_match.group(1))
            continue

        # 匹配本地图片
        local_img = re.match(r'!\[\]\(/([^)]+)\)', line)
        if local_img:
            current_tweet.setdefault("local_images", []).append(f"/{local_img.group(1)}")
            continue

        # 匹配失败图片
        failed_img = re.match(r'<!--\s*FAILED_IMAGE:\s*(.*?)\s*-->', line)
        if failed_img:
            current_tweet.setdefault("failed_images", []).append(failed_img.group(1))
            continue

        # 空行 -> 推文结束
        if line.strip() == "" and current_tweet.get("content"):
            pass

    # 添加最后一条
    if current_tweet and "content" in current_tweet:
        tweets.append(current_tweet)

    return tweets

def download_images(username, new_tweets, max_workers=3):
    """
    下载新推文中的图片
    使用 curl 下载并自动上传到 Telegraph
    """
    import subprocess
    user_images_dir = IMAGES_DIR / username
    user_images_dir.mkdir(exist_ok=True)

    downloaded_count = 0
    failed_count = 0
    telegram_uploaded = 0

    for tweet in new_tweets:
        if not tweet.get("images"):
            continue

        tweet_local_images = []
        tweet_failed_images = []
        tweet_telegraph_urls = []

        for img_url in tweet["images"]:
            # 跳过视频缩略图
            if _is_video_thumbnail(img_url):
                continue

            # 生成文件名
            img_ext = ".jpg"
            url_path = img_url.split("?")[0]
            url_ext = Path(url_path).suffix.lower()
            if url_ext in {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}:
                img_ext = url_ext

            tweet_id = get_tweet_id(tweet.get("link", "")) or "unknown"
            img_filename = f"{tweet_id}_{downloaded_count}{img_ext}"
            img_path = user_images_dir / img_filename

            try:
                # 下载图片
                curl_cmd = ["curl", "-s", "-o", str(img_path), "-w", "%{http_code}", "--connect-timeout", "10", "--max-time", "20", img_url]
                result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=30)

                if result.returncode == 0 and img_path.exists() and img_path.stat().st_size > 0:
                    downloaded_count += 1
                    tweet_local_images.append(f"/images/{username}/{img_filename}")

                    # 上传到 Telegraph
                    if TELEGRAPH_ENABLED:
                        teleg_url = _upload_to_telegraph(img_path, verbose=False)
                        if teleg_url:
                            telegram_uploaded += 1
                            tweet_telegraph_urls.append(teleg_url)

                else:
                    failed_count += 1
                    tweet_failed_images.append(img_url)

            except Exception:
                failed_count += 1
                tweet_failed_images.append(img_url)

        tweet["local_images"] = tweet_local_images
        tweet["failed_images"] = tweet_failed_images
        tweet["telegraph_urls"] = tweet_telegraph_urls

    print(f"\n 📊 图片统计：下载 {downloaded_count} 张，失败 {failed_count} 张")
    print(f" 📤 Telegraph 上传：{telegram_uploaded} 张")

def get_user_output_dir(username):
    return OUTPUT_DIR / username

def get_max_tweets_per_file():
    return MAX_TWEETS

def check_and_push_to_docs(new_tweets, username, daily_file):
    """
    检查并推送新推文到 docs 目录（VitePress）
    将新推文内容追加到每日文档
    """
    doc_dir = OUTPUT_DIR / username
    doc_dir.mkdir(exist_ok=True, parents=True)

    if not new_tweets:
        return

    # 按时间排序（最新的在最前面）
    new_tweets.sort(key=lambda x: x.get("time_obj", datetime.now()), reverse=True)

    # 获取当天的文件名
    date_key = datetime.now().strftime("%Y%m%d")
    daily_file = doc_dir / f"tweets_{date_key}.md"

    # 读取现有内容
    existing_content = ""
    if daily_file.exists():
        existing_content = daily_file.read_text(encoding="utf-8")

    # 检查哪些推文已经存在（按链接去重）
    existing_links = set(re.findall(r'https://x\.com/\w+/status/\d+', existing_content))

    really_new = [t for t in new_tweets if t.get("link") not in existing_links]

    if not really_new:
        return

    # 下载图片
    download_images(username, really_new)

    # 构建新内容
    new_content = ""
    for tweet in really_new:
        time_str = tweet.get("time", "")
        content = tweet.get("content", "")
        link = tweet.get("link", "")

        new_content += f"\n### {time_str}\n\n> {content}\n\n"

        # Telegraph 图片
        for teleg_url in tweet.get("telegraph_urls", []):
            new_content += f"![]({teleg_url})\n\n"

        # 本地图片
        for local_img in tweet.get("local_images", []):
            # 构建 docs public 路径
            img_path = f"/images/{username}/{Path(local_img).name}"
            new_content += f"![{img_path}]({img_path})\n\n"

        # 链接
        new_content += f"[🔗]({link})\n\n"

    # 追加新内容（最新的在最上面）
    if existing_content:
        # 在已有内容前面插入
        full_content = new_content + existing_content
    else:
        full_content = new_content

    # 添加标题
    date_label = datetime.now().strftime("%Y-%m-%d")
    header = f"# @{username} 推文\n\n> 最后更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    full_content = header + full_content

    daily_file.write_text(full_content, encoding="utf-8")
    print(f"\n ✅ 已保存 {len(really_new)} 条新推文到 {daily_file}")

    # 更新 meta
    meta_file = doc_dir / "meta.json"
    current_count = 0
    if meta_file.exists():
        try:
            with open(meta_file, "r") as f:
                meta = json.load(f)
            current_count = meta.get("total_tweets", 0)
        except:
            pass

    # 重新计数
    all_tweet_ids = set()
    for md_file in doc_dir.glob("tweets_*.md"):
        content = md_file.read_text(encoding="utf-8")
        ids = re.findall(r'status/(\d+)', content)
        all_tweet_ids.update(ids)

    meta = {
        "total_tweets": len(all_tweet_ids),
        "latest_tweet_id": max(all_tweet_ids) if all_tweet_ids else "",
        "latest_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tweet_files": [f.name for f in sorted(doc_dir.glob("tweets_*.md"))]
    }
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

def main():
    """主函数"""
    start_time = datetime.now()

    print(f"\n{'='*50}")
    print(f" 📡 X/Twitter 推文抓取 (provider: {PROVIDER})")
    print(f" 🎯 目标用户：{len(TARGET_USERS)} 人")
    print(f" ⏰ 开始时间：{start_time}")
    print(f"{'='*50}\n")

    total_new_tweets = 0
    total_existing = 0
    total_failed_users = 0
    user_stats = {}

    for username, display_name in TARGET_USERS.items():
        print(f"\n{'─'*40}")
        print(f" 👤 {display_name} (@{username})")
        print(f"{'─'*40}")

        try:
            # 获取现有推文 ID
            existing_ids = get_existing_tweet_ids(username)
            existing_count = len(existing_ids)

            # 获取新推文
            print(f"  🔍 正在获取...")
            tweets = fetch_user_tweets(username)

            if not tweets:
                print(f"  ⚠️ 无法获取")
                total_failed_users += 1
                user_stats[username] = {"status": "⚠️ 无法获取", "new": 0, "total": existing_count}
                continue

            # 过滤新推文
            new_tweets = []
            for tweet in tweets:
                tweet_id = get_tweet_id(tweet.get("link", ""))
                if tweet_id and tweet_id not in existing_ids:
                    new_tweets.append(tweet)

            if not new_tweets:
                print(f"  ℹ️ 无新增推文 (共 {len(tweets)} 条)")
            else:
                print(f"  🆕 新推文：{len(new_tweets)} 条")
                total_new_tweets += len(new_tweets)

                # 保存新推文
                doc_dir = OUTPUT_DIR / username
                doc_dir.mkdir(exist_ok=True, parents=True)
                check_and_push_to_docs(new_tweets, username, None)

                # 下载图片
                download_images(username, new_tweets)

            # 汇总统计
            new_total = len(get_existing_tweet_ids(username))  # 重新计算
            user_stats[username] = {
                "status": "✅ 成功" if tweets else "⚠️ 失败",
                "new": len(new_tweets),
                "total": new_total
            }

        except Exception as e:
            print(f"  ❌ 错误：{e}")
            total_failed_users += 1
            user_stats[username] = {"status": f"❌ 错误: {e}", "new": 0, "total": existing_ids}

    # ============ 打印统计报告 ============
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    report_lines = []
    report_lines.append(f"\n{'='*50}")
    report_lines.append(f" 📊 抓取完成")
    report_lines.append(f"{'='*50}")
    report_lines.append(f" ⏱ 耗时：{duration:.1f} 秒")
    report_lines.append(f" 🆕 新增推文：{total_new_tweets}")
    report_lines.append(f" ❌ 失败用户：{total_failed_users}")
    report_lines.append(f"\n{'─'*40}")
    report_lines.append(f" 📋 用户统计")
    report_lines.append(f"{'─'*40}")

    for username, display_name in TARGET_USERS.items():
        stats = user_stats.get(username, {"status": "⚠️ 未执行", "new": 0, "total": "?"})
        report_lines.append(f"  {stats['status']}  @{username} ({display_name}) → 新增 {stats['new']} 条 | 累计 {stats['total']} 条")

    report_text = "\n".join(report_lines)

    print(report_text)

    # 写入统计文件
    STATS_DIR.mkdir(exist_ok=True)
    with open(STATS_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n---\n")
        f.write(f"**运行时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**用时：** {duration:.1f}s\n")
        f.write(f"**新增：** {total_new_tweets} 条\n")
        for username, display_name in TARGET_USERS.items():
            stats = user_stats.get(username, {"status": "⚠️", "new": 0, "total": "?"})
            f.write(f"- @{username} ({display_name}): {stats['status']}, 新增 {stats['new']}, 累计 {stats['total']}\n")

    print(f"\n  📈 统计保存至：{STATS_FILE}")

if __name__ == "__main__":
    main()