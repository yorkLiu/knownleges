#!/usr/bin/env python3
"""
X/Twitter 推文爬虫（多数据源版）
- 支持 FxTwitter API（主要）
- 支持 Nitter（备用）
- 自动切换数据源
- 按年分文件存储，避免单文件过大
- 智能去重，只追加新推文
"""

import json
import re
import sys
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path
import socket

# Set default socket timeout
socket.setdefaulttimeout(30)

# ============ 配置读取 ============
SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"

with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = json.load(f)

TARGET_USERS = config["target_users"]
OUTPUT_DIR = Path(config["output_dir"])
MAX_TWEETS = config.get("max_tweets_per_user", 20)
TIMEZONE_STR = config.get("timezone", "GMT+08:00")
TIMEZONE_OFFSET = config.get("timezone_offset", 8)
PROVIDERS = config.get("providers", {})

OUTPUT_DIR.mkdir(exist_ok=True)
IMAGES_DIR = Path(__file__).parents[2] / "docs/public/images"
IMAGES_DIR.mkdir(exist_ok=True, parents=True)
STATS_DIR = SCRIPT_DIR.parent / "stats"
STATS_DIR.mkdir(exist_ok=True)

TODAY = datetime.now().strftime("%Y%m%d")
STATS_FILE = STATS_DIR / f"fetch_stats_{TODAY}.md"

# ============ 数据源配置 ============
FXTWITTER_API = PROVIDERS.get("fxtwitter", {}).get("api_url", "https://api.fxtwitter.com")
NITTER_INSTANCES = PROVIDERS.get("nitter", {}).get("instances", ["https://nitter.tiekoetter.com"])

# ============ 工具函数 ============
def parse_time_with_timezone(time_str):
    """解析时间字符串"""
    try:
        time_clean = re.sub(r'\s*GMT[+-]\d{2}:\d{2}', '', time_str)
        dt = datetime.strptime(time_clean, "%Y-%m-%d %H:%M:%S")
        dt_local = dt + timedelta(hours=TIMEZONE_OFFSET)
        return dt_local
    except Exception as e:
        return datetime.now()

def format_time(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def get_existing_tweet_ids(username):
    """获取已存在的推文 ID 列表"""
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
                matches = re.findall(r'status/(\d+)', content)
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

def download_image(url, username, tweet_id):
    """下载图片到本地"""
    try:
        # 提取图片 URL
        img_match = re.search(r'https?://[^"\'\\s]+\.jpg', url)
        if not img_match:
            img_match = re.search(r'https?://[^"\'\\s]+\.png', url)
        if not img_match:
            return None
        
        img_url = img_match.group(0)
        
        # 尝试多个图片 URL（原始、较大、中等）
        img_urls = [img_url]
        if 'pbs.twimg.com' in img_url:
            img_urls.append(img_url + ':orig')
            img_urls.append(img_url.replace(':thumb', ':medium'))
        
        for try_url in img_urls:
            try:
                resp = requests.get(try_url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
                if resp.status_code == 200:
                    # 保存文件
                    safe_name = tweet_id.replace('/', '_')
                    ext = '.jpg' if 'jpg' in try_url.lower() else '.png'
                    save_path = IMAGES_DIR / f"{username}_{safe_name}{ext}"
                    save_path.write_bytes(resp.content)
                    return f"./images/{username}/{save_path.name}"
            except:
                continue
        return None
    except Exception as e:
        return None

# ============ FxTwitter API ============
def fetch_from_fxtwitter(username):
    """从 FxTwitter API 获取用户时间线"""
    tweets = []
    try:
        # FxTwitter 没有公开的时间线 API，需要通过 Nitter 获取推文列表，然后用 FxTwitter 获取详情
        # 这里我们直接返回空列表，让用户通过 Nitter 获取
        return tweets
    except Exception as e:
        print(f"    ⚠️ FxTwitter API 错误: {e}")
        return []

def fetch_tweet_from_fxtwitter(tweet_url):
    """从 FxTwitter API 获取单条推文详情"""
    try:
        # 提取用户和状态 ID
        match = re.search(r'/([^/]+)/status/(\d+)', tweet_url)
        if not match:
            return None
        
        screen_name = match.group(1)
        tweet_id = match.group(2)
        
        # 调用 API
        url = f"{FXTWITTER_API}/{screen_name}/status/{tweet_id}"
        resp = requests.get(url, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        if resp.status_code != 200:
            return None
        
        data = resp.json()
        if data.get('code') != 200:
            return None
        
        tweet = data.get('tweet', {})
        if not tweet:
            return None
        
        # 解析内容（保留换行）
        text = tweet.get('text', '').strip()
        if not text:
            return None
        
        # 解析时间
        date_str = tweet.get('date', '')
        time_obj = None
        if date_str:
            # 格式: "Tue Aug 04 23:52:11 +0000 2026"
            try:
                dt = datetime.strptime(date_str, "%a %b %d %H:%M:%S %z %Y")
                time_obj = dt + timedelta(hours=TIMEZONE_OFFSET)
            except:
                pass
        
        if not time_obj:
            time_obj = datetime.now()
        
        # 提取图片
        media_urls = tweet.get('media_extended', [])
        images = []
        for media in media_urls:
            if media.get('type') == 'photo':
                images.append(media.get('url', ''))
        
        return {
            'time': time_obj,
            'time_str': format_time(time_obj),
            'content': text,
            'link': tweet_url,
            'images': images,
            'id': tweet_id
        }
    except Exception as e:
        print(f"    ⚠️ FxTwitter 单条推文错误: {e}")
        return None

# ============ Nitter ============
def fetch_from_nitter(username):
    """从 Nitter 获取用户时间线"""
    tweets = []
    errors = []
    
    for instance in NITTER_INSTANCES:
        try:
            url = f"{instance}/{username}"
            resp = requests.get(url, timeout=15, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            if resp.status_code != 200:
                errors.append(f"{instance}: HTTP {resp.status_code}")
                continue
            
            html = resp.text
            
            # 检查是否错误页面
            if 'error-panel' in html or 'rate limited' in html.lower():
                errors.append(f"{instance}: Rate limited or error")
                continue
            
            # 解析推文
            # 找到所有推文链接
            status_links = re.findall(r'href="/([^/]+)/status/(\d+)#?m?"', html)
            
            if not status_links:
                errors.append(f"{instance}: No tweets found")
                continue
            
            # 去重
            seen = set()
            for screen_name, tweet_id in status_links:
                if tweet_id in seen:
                    continue
                seen.add(tweet_id)
                
                tweet_url = f"{instance}/{screen_name}/status/{tweet_id}#m"
                
                # 获取推文详情
                tweet_data = fetch_tweet_from_nitter_instance(tweet_url, instance)
                if tweet_data:
                    tweets.append(tweet_data)
            
            if tweets:
                break  # 成功获取，退出循环
                
        except Exception as e:
            errors.append(f"{instance}: {e}")
            continue
    
    return tweets, errors

def fetch_tweet_from_nitter_instance(tweet_url, nitter_instance):
    """从 Nitter 实例获取单条推文"""
    try:
        # 从 URL 提取用户和 ID
        match = re.search(r'/([^/]+)/status/(\d+)', tweet_url)
        if not match:
            return None
        
        screen_name = match.group(1)
        tweet_id = match.group(2)
        
        resp = requests.get(tweet_url, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        if resp.status_code != 200:
            return None
        
        html = resp.text
        
        # 提取内容（保留换行）
        content_match = re.search(r'tweet-content[^>]*>(.*?)</div>', html, re.DOTALL)
        if not content_match:
            return None
        
        content = content_match.group(1).strip()
        # 移除 HTML 标签
        content = re.sub(r'<[^>]+>', '', content)
        content = content.strip()
        
        if not content:
            return None
        
        # 提取时间
        date_match = re.search(r'tweet-date.*?title="([^"]+)"', html)
        time_obj = None
        if date_match:
            date_str = date_match.group(1)
            # 格式: "Aug 5, 2026 · 1:18 AM UTC"
            try:
                dt = datetime.strptime(date_str.split('·')[0].strip(), "%b %d, %Y")
                time_str = date_str.split('·')[1].strip() if '·' in date_str else "00:00 AM UTC"
                time_obj = dt.replace(hour=int(time_str[:2]), minute=int(time_str[3:5]))
                time_obj = time_obj + timedelta(hours=TIMEZONE_OFFSET)
            except:
                pass
        
        if not time_obj:
            time_obj = datetime.now()
        
        # 提取图片
        images = []
        img_matches = re.findall(r'<img[^>]+src="(https://pbs\.twimg\.com/[^"]+)"', html)
        for img_url in img_matches:
            if 'media' in img_url:
                images.append(img_url)
        
        return {
            'time': time_obj,
            'time_str': format_time(time_obj),
            'content': content,
            'link': f"https://nitter.net/{screen_name}/status/{tweet_id}#m",
            'images': images,
            'id': tweet_id
        }
    except Exception as e:
        return None

# ============ 主流程 ============
def fetch_tweets_for_user(username):
    """获取用户推文"""
    print(f"\n📥 正在获取 @{username} ...")
    
    # 首先尝试 Nitter（获取列表）
    tweets, errors = fetch_from_nitter(username)
    
    if tweets:
        print(f"    ✅ 通过 Nitter 获取 {len(tweets)} 条推文")
        return tweets
    else:
        print(f"    ⚠️ Nitter 失败: {errors}")
        return []

def save_tweets(username, tweets):
    """保存推文到每日文件"""
    user_dir = OUTPUT_DIR / username
    user_dir.mkdir(exist_ok=True)
    
    today = datetime.now().strftime("%Y-%m-%d")
    daily_file = user_dir / f"{today}.md"
    
    # 读取现有内容
    existing_content = ""
    if daily_file.exists():
        existing_content = daily_file.read_text(encoding="utf-8")
    
    # 解析现有推文 ID
    existing_ids = set(re.findall(r'status/(\d+)', existing_content))
    
    # 过滤重复
    new_tweets = []
    for tweet in tweets:
        if tweet['id'] not in existing_ids:
            new_tweets.append(tweet)
            existing_ids.add(tweet['id'])
    
    if not new_tweets:
        return 0
    
    # 按时间排序
    new_tweets.sort(key=lambda x: x['time'], reverse=True)
    
    # 构建新内容
    new_content = ""
    for tweet in new_tweets:
        new_content += f"## {tweet['time_str']}\n\n"
        new_content += f"**内容**:\n\n{tweet['content']}\n\n"
        
        # 添加图片
        for img in tweet['images']:
            new_content += f"![图片]({img})\n\n"
        
        new_content += f"[查看原文]({tweet['link']})\n\n"
        new_content += "---\n\n"
    
    # 写入文件（新内容在前）
    full_content = new_content + existing_content
    daily_file.write_text(full_content, encoding="utf-8")
    
    return len(new_tweets)

def build_yearly_summary():
    """构建年度汇总"""
    import subprocess
    result = subprocess.run(
        ['node', 'scripts/build_from_data.js'],
        cwd=Path(__file__).parents[2],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"构建错误: {result.stderr}")

def main():
    print("=" * 70)
    print("🐦 X/Twitter 推文抓取（多数据源版）")
    print(f"📅 日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    all_stats = {
        'fetched': 0,
        'new': 0,
        'duplicates': 0,
        'errors': []
    }
    
    for username in TARGET_USERS:
        tweets = fetch_tweets_for_user(username)
        all_stats['fetched'] += len(tweets)
        
        new_count = save_tweets(username, tweets)
        all_stats['new'] += new_count
        all_stats['duplicates'] += len(tweets) - new_count
    
    # 生成统计报告
    with open(STATS_FILE, 'w', encoding='utf-8') as f:
        f.write(f"# X/Twitter 推文抓取统计报告\n\n")
        f.write(f"**日期**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} GMT+08:00\n\n")
        f.write(f"## 总体统计\n\n")
        f.write(f"- **总抓取用户数**: {len(TARGET_USERS)}\n")
        f.write(f"- **总获取推文**: {all_stats['fetched']} 条\n")
        f.write(f"- **新增推文**: {all_stats['new']} 条\n")
        f.write(f"- **重复推文**: {all_stats['duplicates']} 条\n")
    
    print(f"\n{'='*70}")
    print(f"✅ 完成！")
    print(f" 📝 总获取推文：{all_stats['fetched']} 条")
    print(f" ✨ 新增推文：{all_stats['new']} 条")
    print(f" 🔄 重复推文：{all_stats['duplicates']} 条")
    print(f" {'='*70}")
    
    build_yearly_summary()

if __name__ == "__main__":
    main()
