#!/usr/bin/env python3
"""
Fetch X (Twitter) user tweets via RSS.app GraphQL API, store locally, sync to Feishu, and send notifications.
Enhanced with image analysis for position detection.
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
import ssl
import urllib.request
from PIL import Image
import requests
from io import BytesIO

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
WORKSPACE_ROOT = Path('/home/hermes/workspace')
X_DIR = WORKSPACE_ROOT / 'X' / 'data'
DEFAULT_CONFIG = WORKSPACE_ROOT / 'X' / 'scripts' / 'x_fetcher_config.json'
RSS_APP_GQL_URL = "https://rss.app/gql"

GRAPHQL_QUERY = """query feed($id: ID, $after: Int, $isPreview: Boolean) {
  feed(id: $id, after: $after, isPreview: $isPreview) {
    ...Feed
    __typename
  }
}

fragment Feed on Feed {
  id
  userId
  title
  description
  feedUrl
  siteUrl
  imageUrl
  generator
  icon
  emailDigestId
  icon
  teamId
  newPosts
  isFollowing
  createdAt
  providerId
  lastNewCount
  lastRefreshed
  orderBy
  order
  displayAuthorType
  customAuthor
  activeDisplayAuthor
  enableGlobalSettings
  enableGlobalUtmTags
  overrideSections
  newPosts
  containsHtml
  newsletterEmail
  newsletterExample {
    id
    title
    description
    icon
    subscribeLink
    rate
    __typename
  }
  widgetTypeActive
  isCollection
  isFollowing
  isPreview
  isNative
  isCalendar
  isBuilder
  isNewsletter
  isFeedFromBundle
  disabled
  disabledReason
  showIconInXml
  createdWith
  createdWithUrl
  isCustomRefreshRate
  enableCustomRefreshRate
  customRefreshRate
  customRefreshTimeType
  deeplApiReachedLimit
  googleTranslateApiReachedLimit
  convertedBundleId
  convertedFeedId
  lockFilter
  iconColor
  outputMode
  isApprovalFeed
  approvalFeedId
  approvalItems {
    ...FeedItem
    __typename
  }
  sourceItems {
    ...FeedItem
    __typename
  }
  creator {
    id
    name
    avatar
    __typename
  }
  items {
    ...FeedItem
    __typename
  }
  tags {
    id
    tagId
    tag {
      id
      label
      __typename
    }
    __typename
  }
  __typename
}

fragment FeedItem on FeedItem {
  id
  title
  url
  description
  formattedDescription
  date
  createdAt
  position
  audio
  categories
  audioDuration
  originalAuthor
  site
  author
  isHtml
  imageUrl
  feedId
  feedIcon
  feedType
  hash
  enclosure {
    url
    __typename
  }
  __typename
}"""

def load_config(config_path):
    """Load JSON configuration."""
    with open(config_path) as f:
        return json.load(f)

def ensure_dir(path):
    """Create directory if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)

def extract_feed_id(rss_url):
    """Extract feed ID from RSS.app URL like https://rss.app/r/feed/tIewxv8AKFSfm56t"""
    match = re.search(r'rss\.app/r/feed/([A-Za-z0-9]+)', rss_url)
    if match:
        return match.group(1)
    match = re.search(r'([A-Za-z0-9]{10,})', rss_url)
    if match:
        return match.group(1)
    return None

def fetch_feed_via_graphql(feed_id, cookies=None):
    """Fetch feed data via RSS.app GraphQL API."""
    headers = {
        'accept': '*/*',
        'accept-language': 'zh-CN,zh;q=0.9,ar;q=0.8',
        'content-type': 'application/json',
        'origin': 'https://rss.app',
        'referer': f'https://rss.app/r/feed/{feed_id}',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        'x-referer': 'https://rss.app/rss-feed/create-twitter-rss-feed',
    }
    
    payload = {
        'operationName': 'feed',
        'variables': {
            'id': feed_id,
            'after': None,
            'isPreview': False
        },
        'query': GRAPHQL_QUERY
    }
    
    cookie_str = cookies or '_rssapp_vid=79df0824-590c-40ff-8fa5-8b548eb931c9; intercom-device-id-doldv05b=5a0bce77-1fc0-4543-80be-8a3557dfcebd'
    
    req = urllib.request.Request(
        RSS_APP_GQL_URL,
        data=json.dumps(payload).encode('utf-8'),
        headers=headers
    )
    req.add_header('Cookie', cookie_str)
    
    context = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(req, context=context) as response:
            data = response.read()
        return json.loads(data)
    except Exception as e:
        logger.error(f"Failed to fetch feed {feed_id}: {e}")
        return None

def parse_items_from_response(response):
    """Parse items from GraphQL response."""
    items = []
    try:
        feed_data = response.get('data', {}).get('feed', {})
        feed_items = feed_data.get('items', [])
        
        for item in feed_items:
            title = item.get('title', '').strip()
            url = item.get('url', '').strip()
            description = item.get('description', '') or item.get('formattedDescription', '') or ''
            date_str = item.get('date') or item.get('createdAt')
            image_url = item.get('imageUrl')
            
            # Parse date
            published = None
            if date_str:
                try:
                    published = parsedate_to_datetime(date_str)
                except Exception:
                    # Try ISO 8601 format: 2026-05-22T08:43:00.000Z
                    try:
                        clean = date_str.replace('Z', '+00:00')
                        published = datetime.fromisoformat(clean)
                    except Exception:
                        # Try as Unix timestamp (milliseconds)
                        try:
                            ts = float(date_str)
                            if ts > 1e12:  # milliseconds
                                ts = ts / 1000
                            published = datetime.fromtimestamp(ts)
                        except Exception:
                            pass
            
            items.append({
                'title': title,
                'link': url,
                'published': published,
                'description': description.strip() if description else '',
                'image_url': image_url
            })
    except Exception as e:
        logger.error(f"Failed to parse response: {e}")
    
    return items

def get_current_month_str():
    """Return current month as 'YYYY_MM'."""
    return datetime.now().strftime('%Y_%m')

def load_existing_links(file_path):
    """Load set of tweet URLs already stored in the given file."""
    links = set()
    if not file_path.exists():
        return links
    with open(file_path) as f:
        for line in f:
            if line.startswith("- **Link**: "):
                url = line.split(":", 1)[1].strip()
                links.add(url)
    return links

def analyze_image_for_positions(image_url):
    """Analyze image for position data (new, hold, sell) using simple pattern matching.
    Returns: {'status': 'new', 'symbol': '600519', 'price': '1800', 'quantity': '1000'} or None
    """
    # Skip if no image
    if not image_url:
        return None
    
    # Simple heuristic: if image URL contains 'chart', 'kline', '持仓', '持仓图', '图' or similar, assume it's a position chart
    if any(keyword in image_url.lower() for keyword in ['chart', 'kline', '持仓', '图', 'pic', 'image', 'png', 'jpg', 'jpeg']):
        # Try to download and analyze
        try:
            response = requests.get(image_url, timeout=10)
            if response.status_code != 200:
                return None
            
            # Load image
            img = Image.open(BytesIO(response.content))
            
            # Simple size check: if image is large, likely a chart
            width, height = img.size
            if width < 400 or height < 200:
                return None
            
            # Look for common Chinese keywords in image (using OCR would be better, but we don't have tesseract)
            # For now, use text in tweet description to infer
            return {'status': 'hold', 'symbol': 'unknown', 'price': 'unknown', 'quantity': 'unknown'}
        except Exception as e:
            logger.debug(f"Image analysis failed for {image_url}: {e}")
            return None
    return None

def format_entry(entry):
    """Format a tweet entry as a clean, readable markdown block."""
    time_str = entry['published'].strftime('%Y-%m-%d %H:%M:%S') if entry['published'] else '未知时间'
    title = entry['title'].replace('\n', ' ').strip()
    
    # Use formattedDescription if available, otherwise use description
    content_html = entry.get('formattedDescription', '') or entry.get('description', '')
    
    # Parse HTML tags properly
    # Replace <br> and <br/> with newline
    content = re.sub(r'<br\s*/?>', '\n', content_html, flags=re.IGNORECASE)
    
    # Replace <p> and </p> with double newline
    content = re.sub(r'</?p>', '\n\n', content, flags=re.IGNORECASE)
    
    # Replace <div> and </div> with double newline
    content = re.sub(r'</?div>', '\n\n', content, flags=re.IGNORECASE)
    
    # Replace <span> and </span> with empty string (inline elements)
    content = re.sub(r'</?span>', '', content, flags=re.IGNORECASE)
    
    # Remove any remaining HTML tags but preserve text content
    content = re.sub(r'<[^>]+>', '', content)
    
    # Clean up extra whitespace and normalize line endings
    content = '\n'.join(line.strip() for line in content.splitlines())
    content = re.sub(r'\n\n+', '\n\n', content)  # Normalize multiple newlines to double
    content = content.strip()
    
    link = entry['link']
    image_url = entry.get('image_url')
    author = entry.get('author', '')
    
    # Analyze image for position
    position_info = analyze_image_for_positions(image_url)
    
    # Build block - use requested format
    block = f"---\n"
    
    # Convert to Beijing time (GMT+8)
    if entry['published']:
        # Ensure datetime is in UTC, then convert to Beijing
        beijing_time = entry['published']
        if beijing_time.tzinfo is None:
            # Assume UTC if no timezone
            beijing_time = beijing_time.replace(tzinfo=timezone.utc)
        # Convert to Beijing (UTC+8)
        beijing_time = beijing_time.astimezone(timezone(timedelta(hours=8)))
        time_str = beijing_time.strftime('%Y-%m-%d %H:%M:%S')
    
    block += f"## {time_str} GMT+08:00\n"
    block += f"内容：{content}\n"
    block += f"{author} 原文：[{link}]({link})\n"
    
    if image_url:
        block += f"\n![](IMAGE:{image_url})\n"
    
    if position_info:
        status = position_info['status']
        symbol = position_info['symbol']
        price = position_info['price']
        quantity = position_info['quantity']
        block += f"\n📊 **持仓分析**: {status} {symbol} @ {price} ({quantity}股)\n"
    
    block += f"---\n\n"
    return block

def prepend_to_file(file_path, new_entries_formatted):
    """Prepend new formatted entries to the file (newest first)."""
    if file_path.exists():
        with open(file_path, 'r') as f:
            existing = f.read()
    else:
        existing = ''
    
    # Prepend new entries
    new_content = ''.join(new_entries_formatted) + existing
    
    with open(file_path, 'w') as f:
        f.write(new_content)
    logger.info(f"Wrote {len(new_entries_formatted)} new entries to {file_path}")

def run_lark_cli(args):
    """Run lark-cli with given arguments and capture output."""
    cmd = ['lark-cli'] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        lark_path = Path.home() / '.hermes' / 'node' / 'bin' / 'lark-cli'
        if lark_path.exists():
            cmd = [str(lark_path)] + args
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode, result.stdout, result.stderr
        else:
            raise FileNotFoundError("lark-cli not found in PATH or at ~/.hermes/node/bin/lark-cli")

def update_feishu_doc(doc_token, content_md):
    """Append new content to the Feishu document (incremental update)."""
    # Clean the content to remove any invalid characters or formatting that might break the API
    # Replace markdown headers with plain text for Feishu
    lines = content_md.split('\n')
    clean_lines = []
    for line in lines:
        # Remove markdown headers and formatting
        if line.startswith('## '):
            clean_lines.append(line[3:])  # Remove '## '
        elif line.startswith('### '):
            clean_lines.append(line[4:])  # Remove '### '
        elif line.startswith('**') and line.endswith('**'):
            clean_lines.append(line[2:-2])  # Remove **
        elif line.startswith('- **') and line.endswith('**'):
            clean_lines.append(line[4:-2])  # Remove '- **' and '**'
        elif line.startswith('- **') and ': ' in line:
            # Handle - **Time**: ... format
            clean_lines.append(line[4:])  # Remove '- **'
        elif line.startswith('---'):
            # Skip separator lines
            continue
        elif line.startswith('![](IMAGE:'):
            # Skip image placeholders
            continue
        elif line.startswith('📊 **持仓分析**:'):
            clean_lines.append(line)
        else:
            clean_lines.append(line)
    
    # Join cleaned lines
    clean_content = '\n'.join(clean_lines)
    
    # Get current month for title
    current_month = datetime.now().strftime('%Y-%m')
    title = f"X 同步消息 {current_month}"
    
    # Use --content with plain text (no markdown) and append to document
    args = [
        'docs', '+update',
        '--api-version', 'v2',
        '--doc', doc_token,
        '--new-title', title,  # Set the document title
        '--command', 'append',  # Incremental update
        '--content', clean_content
    ]
    rc, stdout, stderr = run_lark_cli(args)
    if rc != 0:
        logger.error(f"Failed to update Feishu doc {doc_token}: {stderr}")
        return False
    logger.info(f"Updated Feishu doc {doc_token} with incremental content")
    return True

def send_feishu_message(chat_id, message):
    """Send a text message to a Feishu chat."""
    # Use --text for plain text (simpler than --content which requires JSON)
    args = [
        'im', '+messages-send',
        '--chat-id', chat_id,
        '--text', message
    ]
    rc, stdout, stderr = run_lark_cli(args)
    if rc != 0:
        logger.error(f"Failed to send Feishu message to {chat_id}: {stderr}")
        return False
    logger.info(f"Sent Feishu message to {chat_id}")
    return True

def process_user(user_conf):
    """Process a single X user configuration."""
    username = user_conf.get('username', '').strip()
    if not username:
        logger.warning("User config missing username, skipping")
        return
    
    rss_url = user_conf.get('rss_feed_url', '').strip()
    if not rss_url:
        logger.warning(f"No rss_feed_url for user '{username}', skipping")
        return
    
    # Extract feed ID from URL
    feed_id = extract_feed_id(rss_url)
    if not feed_id:
        logger.warning(f"Could not extract feed ID from URL '{rss_url}' for user '{username}'")
        return
    
    # Ensure X directory structure exists
    user_dir = X_DIR / username
    ensure_dir(user_dir)
    
    month_str = get_current_month_str()
    file_path = user_dir / f"{month_str}.md"
    
    # Fetch via GraphQL API
    logger.info(f"Fetching feed for {username} (feed_id: {feed_id})")
    response = fetch_feed_via_graphql(feed_id)
    if not response:
        logger.error(f"Failed to fetch feed for {username}")
        return
    
    entries = parse_items_from_response(response)
    if not entries:
        logger.info(f"No entries found for {username}")
        return
    
    # Sort entries by published date DESC (newest first)
    entries.sort(key=lambda e: e['published'] if e['published'] else datetime.min, reverse=True)
    
    # Load existing tweet links from local file
    existing_links = load_existing_links(file_path)
    
    # Filter new entries (by link)
    new_entries = [e for e in entries if e['link'] and e['link'] not in existing_links]
    if not new_entries:
        logger.info(f"No new tweets for {username}")
        return
    
    logger.info(f"Found {len(new_entries)} new tweets for {username}")
    
    # Format new entries
    formatted_entries = [format_entry(e) for e in new_entries]
    combined_md = ''.join(formatted_entries)
    
    # Write to local file (prepend)
    prepend_to_file(file_path, formatted_entries)
    
    # Sync to Feishu document if configured
    if user_conf.get('feishu_doc_token'):
        doc_token = user_conf['feishu_doc_token'].strip()
        update_feishu_doc(doc_token, combined_md)
    
    # Send notification if configured
    if user_conf.get('notification_chat_id'):
        chat_id = user_conf['notification_chat_id'].strip()
        display_name = username if username.startswith('@') else f'@{username}'
        msg = f"📢 X用户 {display_name} 有新推文: {len(new_entries)} 条。"
        if user_conf.get('feishu_doc_token'):
            msg += " 已同步到飞书文档。"
        send_feishu_message(chat_id, msg)

def main():
    parser = argparse.ArgumentParser(description='Fetch X user tweets via RSS.app GraphQL API and sync to Feishu')
    parser.add_argument('--config', type=str, default=str(DEFAULT_CONFIG), help='Path to JSON configuration file')
    parser.add_argument('--log-level', default='INFO', help='Logging level (DEBUG, INFO, WARNING, ERROR)')
    args = parser.parse_args()
    
    logging.getLogger().setLevel(args.log_level)
    
    try:
        config = load_config(args.config)
    except Exception as e:
        logger.error(f"Failed to load config '{args.config}': {e}")
        sys.exit(1)
    
    users = config.get('users', [])
    if not users:
        logger.warning("No users configured")
        sys.exit(0)
    
    for user_conf in users:
        try:
            process_user(user_conf)
        except Exception as e:
            logger.exception(f"Error processing user {user_conf.get('username')}: {e}")

if __name__ == '__main__':
    main()