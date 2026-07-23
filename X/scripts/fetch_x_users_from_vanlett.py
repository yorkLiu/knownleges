#!/usr/bin/env python3
"""
X/Twitter 推文爬虫（vanlett.com 版）
- 使用 vanlett.com 作为数据源（无需认证）
- 支持 Playwright 抓取页面内容
- 按年分文件存储，避免单文件过大
- 智能去重，只追加新推文
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
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
MAX_TWEETS = config.get("max_tweets_per_user", 20)
TIMEZONE_STR = config.get("timezone", "GMT+08:00")
TIMEZONE_OFFSET = config.get("timezone_offset", 8)  # 默认东八区

OUTPUT_DIR.mkdir(exist_ok=True)

# ============ 图片存储配置 ============
IMAGES_DIR = Path(__file__).parents[2] / "docs/public/images"
IMAGES_DIR.mkdir(exist_ok=True, parents=True)

# ============ 统计报告配置 ============
STATS_DIR = SCRIPT_DIR.parent / "stats"
STATS_DIR.mkdir(exist_ok=True)

TODAY = datetime.now().strftime("%Y%m%d")
STATS_FILE = STATS_DIR / f"fetch_stats_{TODAY}.md"

# ============ 工具函数 ============

def parse_time_with_timezone(time_str):
    """解析时间字符串，返回带时区信息的 datetime"""
    try:
        # 移除 GMT 时区信息
        time_clean = re.sub(r'\s*GMT[+-]\d{2}:\d{2}', '', time_str)
        dt = datetime.strptime(time_clean, "%Y-%m-%d %H:%M:%S")
        # 转换为指定时区 (假设解析出的 dt 是 UTC)
        dt_local = dt + timedelta(hours=TIMEZONE_OFFSET)
        return dt_local
    except Exception as e:
        print(f"    ⚠️ 时间解析失败：{time_str} ({e})")
        return datetime.now()

def format_time(dt):
    """将 datetime 对象格式化为字符串"""
    return dt.strftime("%Y-%m-%d %H:%M:%S")

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
        # Extract content: try **内容**: format first, then fall back to raw content between tags and [查看原文]
        content_match = re.search(r'\*\*内容\*\*:\s*\n\n(.+?)(?=\n\n\*\*图片\*\*:|$)', tweet_body, re.DOTALL)
        if content_match:
            tweet_content = content_match.group(1).strip()
        else:
            # New format (no **内容**: label): extract content between tags/time and [查看原文]/---/img
            # Remove the time header line and tags
            body_after_header = re.sub(r'^## .+?\n+', '', tweet_body, flags=re.DOTALL)
            body_after_header = re.sub(r'^<a href="[^"]*tag=[^"]+">[^<]+</a>\s*\n+', '', body_after_header)
            # Content ends at [查看原文], <img, or ---
            content_end = re.search(r'(\[查看原文\]|<img|---)', body_after_header)
            if content_end:
                tweet_content = body_after_header[:content_end.start()].strip()
            else:
                tweet_content = body_after_header.strip()
        # Remove any <img> tags or [查看原文] links that leaked into content from previous runs
        tweet_content = re.sub(r'<img[^>]+>', '', tweet_content)
        tweet_content = re.sub(r'\[查看原文\]\([^)]+\)', '', tweet_content)
        
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
                
                f.write(f"{tweet['content']}\n\n")
                
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
    
    return user_dir, True, 0


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
        
        # 收集所有推文内容（去重：按内容+时间戳过滤）
        all_tweets = []
        seen_keys = set()
        for daily_file in daily_files:
            try:
                with open(daily_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    # 按推文分割（每个推文以 "## 时间" 开始，以 "---" 结束）
                    sections = content.split("---\n\n")
                    for section in sections:
                        if section.strip().startswith("## "):
                            # 提取时间戳和内容作为去重键
                            ts_match = re.match(r'^## (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', section.strip(), re.MULTILINE)
                            # Try **内容**: format, then fall back to content between tags and [查看原文]/img
                            content_match = re.search(r'\*\*内容\*\*:\s*\n\n(.+?)(?=\n\n\*\*图片\*\*:|$)', section.strip(), re.DOTALL)
                            if ts_match:
                                if content_match:
                                    key = (ts_match.group(1), content_match.group(1).strip())
                                else:
                                    # New format: extract content from section for dedup key
                                    raw = re.sub(r'^## .+?\n+', '', section.strip(), flags=re.DOTALL)
                                    raw = re.sub(r'^<a href="[^"]*tag=[^"]+">[^<]+</a>\s*\n+', '', raw)
                                    raw = re.sub(r'\s*\[查看原文\]\([^)]+\).*$', '', raw, flags=re.DOTALL)
                                    raw = re.sub(r'\s*<img[^>]+>.*$', '', raw, flags=re.DOTALL)
                                    key = (ts_match.group(1), raw.strip())
                                if key not in seen_keys:
                                    seen_keys.add(key)
                                    # Strip any **内容**: label before writing to yearly summary
                                    cleaned_section = re.sub(r'\*\*内容\*\*:\s*\n\n', '', section.strip())
                                    all_tweets.append(cleaned_section)
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
            # 处理重复时间戳：给相同时间戳的推文加后缀避免 VitePress ID 冲突
            ts_seen = {}  # 基础时间戳 -> 出现次数
            for tweet_section in reversed(all_tweets):
                # 匹配 ## YYYY-MM-DD HH:MM:SS 或 ## YYYY-MM-DD HH:MM:SS-N
                ts_match = re.match(r'^## (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})(?:-(\d+))?', tweet_section, re.MULTILINE)
                if ts_match:
                    base_ts = ts_match.group(1)
                    suffix = ts_match.group(2)  # 已有的后缀（None 表示无后缀）
                    count = ts_seen.get(base_ts, 0) + 1
                    ts_seen[base_ts] = count
                    
                    if suffix is None and count > 1:
                        # 已经有重复了，给当前这条加后缀
                        old_header = f'## {base_ts}'
                        new_header = f'## {base_ts}-{count}'
                        tweet_section = tweet_section.replace(old_header, new_header, 1)
                    elif suffix is not None:
                        # 已有后缀，确保唯一（如果后缀等于 count，跳过）
                        if int(suffix) != count:
                            old_header = f'## {base_ts}-{suffix}'
                            new_header = f'## {base_ts}-{count}'
                            tweet_section = tweet_section.replace(old_header, new_header, 1)
                
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
    from playwright.sync_api import sync_playwright
    
    print("=" * 70)
    print("🚀 X/Twitter 推文爬虫 (vanlett.com 版)")
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
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        for username, description in TARGET_USERS.items():
            print(f"📥 正在获取 @{username} ({description})...", end=" ")
            
            # 从 vanlett.com 获取推文
            tweets = fetch_tweets_from_vanlett(browser, username)
            
            if tweets:
                print(f"✅ {len(tweets)} 条推文")
                
                user_stats = {'fetched': 0, 'new': 0, 'duplicates': 0}
                user_dir, has_new, downloaded_imgs = save_to_markdown(username, description, tweets, user_stats)
                
                if has_new:
                    print(f" 💾 已保存到：{user_dir.name} (新增 {user_stats['new']} 条)")
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
        
        browser.close()
    
    print("\n📋 正在生成统计报告...", end=" ")
    save_stats_report(all_stats)
    print(f"✅ {STATS_FILE.name}\n")

    print("=" * 70)
    print(f"✅ 完成！")
    print(f" 📊 成功同步：{all_stats['total_users']} 个用户")
    print(f" 📝 总获取推文：{all_stats['fetched']} 条")
    print(f" ✨ 新增推文：{all_stats['new']} 条")
    print(f" 🔄 重复推文：{all_stats['duplicates']} 条")
    print(f" 🕐 时区：{TIMEZONE_STR}")
    print("=" * 70)
    build_yearly_summary()


def fetch_tweets_from_vanlett(browser, username):
    """从 vanlett.com 获取用户推文"""
    try:
        page = browser.new_page()
        page.goto(f"https://vanlett.com/{username}", wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(5000)
        
        # 提取推文
        tweets_raw = page.evaluate("""() => {
            const postBodies = document.querySelectorAll('.post-body');
            const results = [];
            postBodies.forEach((body, i) => {
                if (i < 20) {  // 最多取20条
                    const header = document.querySelectorAll('.post-header')[i]?.innerText?.trim() || '';
                    const content = document.querySelectorAll('.post-content')[i]?.innerText?.trim() || '';
                    const stats = document.querySelectorAll('.post-stats')[i]?.innerText?.trim() || '';
                    results.push({
                        header: header,
                        content: content,
                        stats: stats,
                        className: body.className
                    });
                }
            });
            return results;
        }""")
        
        tweets = []
        for tweet_raw in tweets_raw:
            # 解析 header 获取时间和链接
            header = tweet_raw['header']
            content = tweet_raw['content']
            
            # 提取时间戳
            time_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', header)
            if time_match:
                time_str = time_match.group(1)
                time_obj = parse_time_with_timezone(time_str)
            else:
                # 尝试从 header 中提取日期
                date_match = re.search(r'([A-Z][a-z]{2} \d{1,2})', header)
                if date_match:
                    date_str = date_match.group(1)
                    # 转换为标准格式
                    try:
                        dt = datetime.strptime(f"{date_str} {datetime.now().year}", "%b %d %Y")
                        time_obj = dt
                        time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        time_obj = datetime.now()
                        time_str = "Unknown"
                else:
                    time_obj = datetime.now()
                    time_str = "Unknown"
            
            # 构建推文链接
            tweet_link = f"https://x.com/{username}/status/..."  # vanlett 没有直接的状态链接
            
            tweets.append({
                'content': content,
                'link': tweet_link,
                'time': time_str,
                'time_obj': time_obj,
                'user': username,
                'images': [],  # vanlett 页面不包含图片链接
                'local_images': [],
                'failed_images': []
            })
        
        return tweets
        
    except Exception as e:
        print(f"    ❌ 获取失败：{e}")
        return []
    finally:
        page.close()


if __name__ == "__main__":
    main()
