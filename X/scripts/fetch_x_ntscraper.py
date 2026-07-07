#!/usr/bin/env python3
"""
X/Twitter 推文抓取工具（基于 ntscraper 库 + Nitter fallback）

使用非官方 API 直接从 X/Twitter 抓取，不依赖 nitter 或 RSSHub。
完全缓存友好，智能去重，图片自动上传 Telegraph。
自动选择最稳定的 Nitter 实例。
"""

import re
import json
from datetime import datetime
from pathlib import Path
from html import escape
import urllib.request
import urllib.error
import subprocess

# Monkey-patch ntscraper 的 _get_instances 方法，添加稳定的备用实例
# 解决 libredirect 实例列表不可用的问题
import ntscraper.nitter as nitter_module
_original_get_instances = nitter_module.Nitter._get_instances

FALLBACK_INSTANCES = [
    "https://nitter.tiekoetter.com",
    "https://nitter.privacyredirect.com",
    "https://nitter.net",
    "https://xcancel.com",
    "https://nitter.poast.org",
    "https://nitter.space",
]

def _patched_get_instances(self):
    try:
        return _original_get_instances(self)
    except Exception:
        return FALLBACK_INSTANCES

nitter_module.Nitter._get_instances = _patched_get_instances

from ntscraper import Nitter
import nitter_utils

# ============ 配置读取 ============
SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"

with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = json.load(f)

TARGET_USERS = config["target_users"]
OUTPUT_DIR = Path(config["output_dir"])
MAX_TWEETS = config.get("max_tweets_per_user", 20)
TELEGRAPH_ENABLED = config.get("telegraph_enabled", True)
TELEGRAPH_BASE_URL = config.get("telegraph_base_url", "https://telegraph-image-fork.pages.dev")
TELEGRAPH_CACHE_FILE = SCRIPT_DIR / "telegraph_cache.json"

OUTPUT_DIR.mkdir(exist_ok=True)

# Telegraph 图床配置
IMAGES_DIR = Path(__file__).parents[2] / "docs/public/images"
IMAGES_DIR.mkdir(exist_ok=True, parents=True)

# ============ 工具函数 ============

def load_cache():
    """加载 Telegraph 上传缓存"""
    if TELEGRAPH_CACHE_FILE.exists():
        try:
            with open(TELEGRAPH_CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_cache(cache):
    """保存 Telegraph 上传缓存"""
    with open(TELEGRAPH_CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def get_tweet_id(link):
    """从推文链接中提取推文 ID"""
    match = re.search(r"status/(\d+)", link)
    if match:
        return match.group(1)
    return None

def get_existing_tweet_ids(username):
    """获取已存在的推文 ID"""
    user_dir = OUTPUT_DIR / username
    if not user_dir.exists():
        return set()

    existing_ids = set()
    try:
        for daily_file in user_dir.glob("*.md"):
            if daily_file.name == "meta.json":
                continue
            content = daily_file.read_text(encoding="utf-8")
            ids = re.findall(r"status/(\d+)", content)
            existing_ids.update(ids)
    except:
        pass
    return existing_ids

def download_tweet_images(tweet, username):
    """下载推文中的图片并上传到 Telegraph"""
    tweet_local_images = []
    tweet_telegraph_urls = []

    cache = load_cache()
    user_images_dir = IMAGES_DIR / username
    user_images_dir.mkdir(exist_ok=True)

    for i, img_url in enumerate(tweet.get("images", [])):
        # 简单的图片 URL 处理
        img_ext = ".jpg"
        if "?" in img_url:
            img_url = img_url.split("?")[0]
        url_ext = Path(img_url).suffix.lower()
        if url_ext in {".jpg", ".jpeg", ".png", ".gif"}:
            img_ext = url_ext

        tweet_id = tweet.get("link", "").split("status/")[-1] or "unknown"
        img_filename = f"{tweet_id}_{i}{img_ext}"
        img_path = user_images_dir / img_filename

        try:
            if img_filename in cache:
                tweet_telegraph_urls.append(cache[img_filename])
                continue

            # 使用 curl 下载
            headers = {
                "User-Agent": "Mozilla/5.0"
            }
            req = urllib.request.Request(img_url, headers=headers)
            resp = urllib.request.urlopen(req, timeout=20)
            img_data = resp.read()

            # 保存到本地
            with open(img_path, "wb") as f:
                f.write(img_data)
            tweet_local_images.append(f"/images/{username}/{img_filename}")

            # 上传 Telegraph (模拟)
            if TELEGRAPH_ENABLED:
                try:
                    upload_cmd = ["curl", "-s", "-F", f"file=@{img_path}", f"{TELEGRAPH_BASE_URL}/upload"]
                    result = subprocess.run(upload_cmd, capture_output=True, text=True, timeout=15)
                    if result.returncode == 0 and result.stdout:
                        try:
                            upload_resp = json.loads(result.stdout)
                            if upload_resp and isinstance(upload_resp, list) and upload_resp[0].get("src"):
                                teleg_url = f"{TELEGRAPH_BASE_URL}{upload_resp[0]['src']}"
                                tweet_telegraph_urls.append(teleg_url)
                                cache[img_filename] = teleg_url
                                save_cache(cache)
                        except:
                            pass
                except Exception as e:
                    print(f"  ⚠️ Telegraph 上传失败: {e}")
                    
        except Exception as e:
            print(f"  ❌ 图片下载失败: {e}")

    tweet["telegraph_urls"] = tweet_telegraph_urls
    tweet["local_images"] = tweet_local_images

    return tweet

def save_tweet_to_markdown(tweet, username):
    """将推文保存为 Markdown 格式"""
    user_dir = OUTPUT_DIR / username
    user_dir.mkdir(exist_ok=True)

    # 构建文件名和内容
    tweet_id = get_tweet_id(tweet.get("link", "")) or tweet.get("date", "").replace(":", "").replace("-", "").replace(" ", "_")
    date_key = datetime.strptime(tweet["date"], "%b %d, %Y").strftime("%Y%m%d")
    md_file = user_dir / f"tweets_{date_key}.md"

    content = """
### {tweet['date']}

> {tweet.get('content', '').replace('\n', ' ')}

"""

    # 添加图片
    for teleg_url in tweet.get("telegraph_urls", []):
        content += f"![]({teleg_url})\n\n"
    
    content += f"[🔗]({tweet.get('link')})\n\n"

    # 检查是否已存在（按 link 去重）
    if md_file.exists():
        existing = md_file.read_text(encoding="utf-8")
        if tweet.get("link", "") in existing:
            return md_file

    # 追加新内容
    if not md_file.exists():
        content = f"# @{username} 推文\n\n> 最后更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n" + content
    else:
        existing_content = md_file.read_text(encoding="utf-8")
        content = existing_content + "\n---\n" + content

    md_file.write_text(content, encoding="utf-8")
    print(f"  ✅ 保存推文到 {md_file}")
    
    # 更新元数据
    update_tweet_metadata(username)
    return md_file

def update_tweet_metadata(username):
    """更新用户推文元数据"""
    user_dir = OUTPUT_DIR / username
    user_dir.mkdir(exist_ok=True)
    meta_file = user_dir / "meta.json"

    tweet_ids = set()
    for md_file in user_dir.glob("tweets_*.md"):
        content = md_file.read_text(encoding="utf-8")
        ids = re.findall(r"status/(\d+)", content)
        tweet_ids.update(ids)

    meta = {
        "total_tweets": len(tweet_ids),
        "latest_tweet_id": max(tweet_ids) if tweet_ids else None,
        "latest_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tweet_files": [f.name for f in sorted(user_dir.glob("tweets_*.md"))]
    }
    
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

# ============ 主程序 ============

def fetch_user_tweets(username, max_tweets=MAX_TWEETS):
    """抓取用户推文"""
    # 获取最佳 Nitter 实例
    best_instance = nitter_utils.get_best_instance()
    scraper = Nitter(instances=[best_instance])
    print(f"  🔍 抓取 @{username}... (使用实例: {best_instance})")

    try:
        # 获取已有的推文 ID
        existing_ids = get_existing_tweet_ids(username)
        print(f"    已存在: {len(existing_ids)}")

        # 抓取新推文
        tweets = scraper.get_tweets(username, mode="user", number=max_tweets)
        if not tweets or "tweets" not in tweets:
            print(f"    ❌ 抓取失败")
            return False

        new_tweets = 0
        for tweet in tweets["tweets"]:
            tweet_id = get_tweet_id(tweet.get("link", ""))
            if tweet_id and tweet_id in existing_ids:
                continue

            print(f"    🆕 新推文: {tweet['date']}")
            tweet = download_tweet_images(tweet, username)
            save_tweet_to_markdown(tweet, username)
            new_tweets += 1

        print(f"    ✅ 新增推文: {new_tweets} 条")
        return True

    except Exception as e:
        print(f"    ❌ 错误: {e}")
        return False

def main():
    print(f"\n{'='*50}")
    print(f" 🐦 X/Twitter 推文抓取 (ntscraper)")
    print(f" 🎯 目标用户: {len(TARGET_USERS)} 人")
    print(f" ⏰ 开始抓取: {datetime.now()}")
    print(f"{'='*50}\n")

    start_time = datetime.now()
    for username, display_name in TARGET_USERS.items():
        print(f"\n{'─'*40}")
        print(f" 👤 {display_name} (@{username})")
        print(f"{'─'*40}")
        fetch_user_tweets(username)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    print(f"\n{'='*50}")
    print(f" 📊 抓取完成（用时: {duration:.1f}s）")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    main()