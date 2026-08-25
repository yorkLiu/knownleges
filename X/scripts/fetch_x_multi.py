#!/usr/bin/env python3
"""
X/Twitter 推文爬虫（多数据源版 - 带重试）
- 主要: Nitter.tiekoetter.com (时间线)
- 备用: FxTwitter API (单条推文详情)
- 自动重试 + 数据源切换
- 保留原文换行
"""

import json
import re
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path

# 配置
CONFIG_FILE = Path(__file__).parent / "config.json"
with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = json.load(f)

TARGET_USERS = config["target_users"]
OUTPUT_DIR = Path(config["output_dir"])
MAX_TWEETS = config.get("max_tweets_per_user", 20)
TIMEZONE_OFFSET = config.get("timezone_offset", 8)

# 数据源
NITTER_INSTANCE = "https://nitter.tiekoetter.com"
FX_TWITTER_API = "https://api.fxtwitter.com"

IMAGES_DIR = Path(__file__).parents[2] / "docs/public/images"
IMAGES_DIR.mkdir(exist_ok=True, parents=True)

def fetch_tweet_detail(screen_name, tweet_id, retries=3):
    """从 FxTwitter API 获取推文详情（带重试）"""
    for i in range(retries):
        try:
            url = f"{FX_TWITTER_API}/{screen_name}/status/{tweet_id}"
            resp = requests.get(url, timeout=15, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            if resp.status_code != 200:
                time.sleep(1)
                continue
            
            data = resp.json()
            if data.get('code') != 200:
                time.sleep(1)
                continue
            
            tweet = data.get('tweet', {})
            if not tweet:
                continue
            
            text = tweet.get('text', '').strip()
            if not text:
                continue
            
            # 解析时间
            date_str = tweet.get('created_at', '')
            time_obj = None
            if date_str:
                try:
                    dt = datetime.strptime(date_str, "%a %b %d %H:%M:%S %z %Y")
                    time_obj = dt + timedelta(hours=TIMEZONE_OFFSET)
                except:
                    pass
            
            if not time_obj:
                time_obj = datetime.now()
            
            # 提取图片
            images = []
            media = tweet.get('media', {})
            for photo in media.get('photos', []):
                images.append(photo.get('url', ''))
            
            return {
                'time': time_obj,
                'time_str': time_obj.strftime("%Y-%m-%d %H:%M:%S"),
                'content': text,
                'link': f"https://x.com/{screen_name}/status/{tweet_id}",
                'images': images,
                'id': tweet_id
            }
        except Exception as e:
            if i < retries - 1:
                time.sleep(1)
    return None

def fetch_timeline_from_nitter(username, retries=3):
    """从 Nitter 获取时间线（带重试）"""
    for attempt in range(retries):
        try:
            url = f"{NITTER_INSTANCE}/{username}"
            resp = requests.get(url, timeout=20, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            if resp.status_code != 200:
                time.sleep(2)
                continue
            
            html = resp.text
            
            # 检查是否错误页面
            if len(html) < 5000 or 'error-panel' in html or 'rate limited' in html.lower():
                if attempt < retries - 1:
                    time.sleep(3)
                    continue
                return []
            
            # 解析推文链接
            links = re.findall(r'href="/([^/]+)/status/(\d+)#?m?"', html)
            if not links:
                return []
            
            # 获取推文详情
            tweets = []
            seen = set()
            for screen_name, tweet_id in links[:MAX_TWEETS]:
                if tweet_id in seen:
                    continue
                seen.add(tweet_id)
                
                tweet_data = fetch_tweet_detail(screen_name, tweet_id)
                if tweet_data:
                    tweets.append(tweet_data)
            
            return tweets
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
    return []

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
    print("🐦 X/Twitter 推文抓取（多数据源版 - 带重试）")
    print(f"📅 日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📡 数据源: Nitter ({NITTER_INSTANCE})")
    print(f"🔄 备用: FxTwitter API ({FX_TWITTER_API})")
    print("=" * 70)
    
    total_new = 0
    total_fetched = 0
    
    for username in TARGET_USERS:
        print(f"\n📥 正在获取 @{username} ...")
        
        tweets = fetch_timeline_from_nitter(username)
        total_fetched += len(tweets)
        
        if tweets:
            print(f"    ✅ 获取 {len(tweets)} 条推文")
        else:
            print(f"    ⚠️ 无法获取时间线（Nitter 可能 rate limited）")
        
        # 保存推文
        new_count = save_tweets(username, tweets)
        total_new += new_count
    
    print(f"\n{'='*70}")
    print(f"✅ 完成！")
    print(f" 📝 总获取推文: {total_fetched} 条")
    print(f" ✨ 新增推文: {total_new} 条")
    print(f" {'='*70}")
    
    build_yearly_summary()

if __name__ == "__main__":
    main()
