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
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from html.parser import HTMLParser
import urllib.request
import urllib.error
import urllib.parse
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

# ============ Syndication API 配置（首选数据源） ============
# X 官方嵌入端点，替代已停服的 Nitter。需用户 cookie（cf_clearance 绑定出口 IP）。
# 仅保留 ~20 条最新窗口，不能翻历史。
SYNDICATION_URL = config.get(
    "syndication_url", "https://syndication.twitter.com/srv/timeline-profile/screen-name/{}")
COOKIE_FILE = config.get(
    "cookie_file", "/data/hermes/.hermes/scripts/x_cookie.txt")
SYNDICATION_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 " \
                 "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

def _load_cookie():
    """读取 X 用户 cookie 字符串，缺失返回空串"""
    try:
        p = Path(COOKIE_FILE)
        if p.exists():
            return p.read_text(encoding="utf-8").strip()
    except Exception as e:
        print(f" ❌ 读取 cookie 失败：{e}")
    return ""

# ============ DNS 兜底（系统 DNS 被污染时自动 DoH 钉 IP） ============
# 本机 systemd-resolved 上游为中国系 DNS，对 *.twitter.com / *.twimg.com 会返回
# 垃圾应答（如 2001::1 → Errno 101 "Network is unreachable"，或别人的 IPv4 导致超时），
# 而 1.1.1.1 / 8.8.8.8 字面 IP 直连始终可达。系统 DNS 探测失败时自动切 DoH
# （DNS-over-HTTPS）取真实 Cloudflare IP 并钉 IP 直连（SNI/Host/证书校验均用真域名）。
_DOH_ENDPOINTS = [
    ("1.1.1.1", "cloudflare-dns.com", "/dns-query?name={q}&type=A"),
    ("8.8.8.8", "dns.google", "/resolve?name={q}&type=A"),
]
_DOH_CACHE = {}    # host -> [ip]
_PINNED_IPS = {}   # host -> [ip]（空列表 = 系统 DNS 正常，无需钉 IP）

def _doh_resolve(host):
    """通过 DoH（字面 IP 直连，绕开被污染的本地 DNS）查询 host 的真实 A 记录，跟随 CNAME"""
    if host in _DOH_CACHE:
        return _DOH_CACHE[host]
    import http.client
    import ssl
    result = []
    for ip, doh_host, tpl in _DOH_ENDPOINTS:
        try:
            ctx = ssl.create_default_context()
            name = host
            for _hop in range(6):  # CNAME 跟随上限
                conn = http.client.HTTPSConnection(ip, 443, context=ctx, timeout=10)
                conn.request("GET", tpl.format(q=name), headers={
                    "Host": doh_host, "User-Agent": "x-scraper-doh",
                    "accept": "application/dns-json"})
                resp = conn.getresponse()
                data = json.loads(resp.read().decode())
                conn.close()
                recs = data.get("Answer", [])
                a_recs = [x["data"] for x in recs if x.get("type") == 1]
                if a_recs:
                    result = a_recs
                    break
                c_recs = [x for x in recs if x.get("type") == 5]
                if c_recs:
                    name = c_recs[0]["data"]
                    continue
                break
            if result:
                break
        except Exception:
            continue
    _DOH_CACHE[host] = result
    return result

def _is_x_domain(host):
    return bool(host) and (host.endswith(".twitter.com") or host.endswith(".twimg.com"))

def _dns_ok(host):
    """快速探测系统 DNS 是否可用；全不可达则返回 DoH 钉死 IP（空列表 = 系统 DNS 正常）"""
    import socket
    if host in _PINNED_IPS:
        return _PINNED_IPS[host]
    try:
        candidates = [r[4][0] for r in socket.getaddrinfo(host, 443, socket.AF_INET, socket.SOCK_STREAM)]
    except Exception:
        candidates = []
    for ip in candidates:
        try:
            s = socket.create_connection((ip, 443), timeout=2.5)
            s.close()
            _PINNED_IPS[host] = []
            return []
        except Exception:
            continue
    ips = [a for a in _doh_resolve(host) if a and ":" not in a]
    if ips:
        _PINNED_IPS[host] = ips
        print(f"  ⚠️  {host} 系统 DNS 不可达，已切换 DoH 钉死 IP {ips[:2]}")
    else:
        print(f"  ❌ {host} 系统 DNS 与 DoH 均失败")
    return _PINNED_IPS.get(host, [])

_REAL_GETADDRINFO = None  # 首次钉 IP 时惰性初始化

def _open_pinned(url, headers, timeout, host, ips):
    """逐 IP 钉死后发 HTTPS 请求；SNI/Host/证书校验均使用真实域名"""
    import socket
    global _REAL_GETADDRINFO
    if _REAL_GETADDRINFO is None:
        _REAL_GETADDRINFO = socket.getaddrinfo
    last_err = None
    for ip in ips:
        def _gai(h, p, *args, **kwargs):
            if h == host and (not args or args[0] in (0, socket.AF_INET)):
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, p))]
            return _REAL_GETADDRINFO(h, p, *args, **kwargs)
        socket.getaddrinfo = _gai
        try:
            req = urllib.request.Request(url, headers=headers)
            return urllib.request.urlopen(req, timeout=timeout)
        except Exception as e:
            last_err = e
        finally:
            socket.getaddrinfo = _REAL_GETADDRINFO
    raise last_err if last_err else RuntimeError(f"{host} 所有钉死 IP 均失败")

def urlopen_x(url, headers, timeout=30):
    """X 域名 HTTPS 请求入口：系统 DNS 被污染时自动走 DoH 钉 IP，其他域名正常直连"""
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or ""
    if _is_x_domain(host):
        pinned = _dns_ok(host)
        if pinned:
            return _open_pinned(url, headers, timeout, host, pinned)
    req = urllib.request.Request(url, headers=headers)
    return urllib.request.urlopen(req, timeout=timeout)

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

        # 下载图片（pbs.twimg.com 域名经 urlopen_x：系统 DNS 被污染时自动 DoH 钉 IP）
        for attempt in range(retry):
            try:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                with urlopen_x(image_url, headers, timeout=60) as response:
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

def parse_syndication_time(time_str):
    """Syndication created_at: 'Mon Sep 14 00:08:53 +0000 2026' -> 东八区 naive datetime
    （与旧 Nitter 路径一致，返回 naive，配 format_time 使用）"""
    if not time_str:
        return datetime.now()
    try:
        dt = datetime.strptime(time_str, "%a %b %d %H:%M:%S %z %Y")
        local_tz = timezone(timedelta(hours=TIMEZONE_OFFSET))
        return dt.astimezone(local_tz).replace(tzinfo=None)
    except Exception as ex:
        print(f"    ⚠️ syndication 时间解析失败：{time_str} ({ex})")
        return datetime.now()

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

def fetch_user_tweets_nitter(username):
    """从 Nitter RSS 获取用户推文（Syndication 失败时回退）"""
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
        print(f" ❌ Nitter 回退获取失败：{e}")
        return []

def fetch_user_tweets_syndication(username):
    """从 X Syndication API 获取用户时间线（官方嵌入端点，替代已停服的 Nitter）
    
    返回与 fetch_user_tweets_nitter 相同结构的 list，使下游 save_to_markdown 无需改动。
    - content: full_text（RT 自带 'RT @user:' 前缀，与旧 md 风格一致）
    - link: https://x.com/{user}/status/{id}
    - images: entities.media[].media_url_https（pbs.twimg.com 直链，可下载）
    - time: 东八区 naive datetime（与旧 Nitter 路径一致）
    返回 [] 表示无内容（账号注销/删光推文/cookie 失效），触发 Nitter 回退。
    """
    cookie = _load_cookie()
    url = SYNDICATION_URL.format(username)
    headers = {
        "Cookie": cookie,
        "User-Agent": SYNDICATION_UA,
        "Referer": "https://syndication.twitter.com/",
        "Accept": "text/html,application/xhtml+xml",
    }
    try:
        # 经 urlopen_x：系统 DNS 被污染时自动 DoH 钉 IP 直连，否则正常直连
        with urlopen_x(url, headers, timeout=30) as resp:
            html = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print(f" ❌ Syndication 403（cf_clearance 出口 IP 不匹配或 cookie 失效）")
        else:
            print(f" ❌ Syndication HTTP {e.code}")
        return []
    except Exception as e:
        print(f" ❌ Syndication 请求失败：{e}")
        return []
    
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    if not m:
        print(f" ❌ Syndication 响应缺少 __NEXT_DATA__（size={len(html)}）")
        return []
    try:
        page_props = json.loads(m.group(1))["props"]["pageProps"]
    except Exception as e:
        print(f" ❌ Syndication JSON 解析失败：{e}")
        return []
    
    entries = (page_props.get("timeline") or {}).get("entries") or []
    processed = []
    for e in entries:
        t = (e.get("content") or {}).get("tweet")
        if not t or not t.get("id_str"):
            continue
        created = t.get("created_at") or ""
        pub_time = parse_syndication_time(created)
        images = [
            mm.get("media_url_https")
            for mm in ((t.get("entities") or {}).get("media") or [])
            if mm.get("media_url_https")
        ]
        processed.append({
            "content": (t.get("full_text") or t.get("text") or "").replace("\xa0", " "),
            "link": f"https://x.com/{username}/status/{t.get('id_str')}",
            "time": format_time(pub_time),
            "time_obj": pub_time,
            "user": username,
            "images": images,
        })
    return processed

def fetch_user_tweets(username):
    """获取用户推文：Syndication 为主，失败回退 Nitter RSS。
    
    返回推文 dict 列表；账号注销/无内容时返回空列表（由 main 标记为 ⚠️）。
    """
    tweets = fetch_user_tweets_syndication(username)
    if tweets:
        return tweets
    # Syndication 空（注销/删光/403），尝试 Nitter 回退（通常也已停服）
    fallback = fetch_user_tweets_nitter(username)
    if fallback:
        print(f"   ↩️  已回退到 Nitter RSS")
        return fallback
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
        # Extract content (strip any embedded <img> tags to prevent duplication on re-runs)
        content_match = re.search(r'\*\*内容\*\*:\s*\n\n(.+?)(?=\n\n\*\*图片\*\*:|$)', tweet_body, re.DOTALL)
        tweet_content = content_match.group(1).strip() if content_match else ""
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
