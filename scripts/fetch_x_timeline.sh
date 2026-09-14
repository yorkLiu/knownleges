#!/usr/bin/env bash
# fetch_x_timeline.sh <screen_name> [cookie_file]
# 通过 X Syndication API 抓取用户时间线（__NEXT_DATA__ 解析），输出 JSON。
# 用法:
#   ./fetch_x_timeline.sh Mimiwftt                 # 使用默认 cookie 文件
#   ./fetch_x_timeline.sh Mimiwftt /path/to/cookie  # 指定 cookie 文件
#   输出: stdout = JSON（timeline entries），stderr = 进度/错误
# 注意: cookie 含 cf_clearance 时须从同一出口 IP 访问，否则会 403。

set -euo pipefail

SCREEN="${1:?用法: $0 <screen_name> [cookie_file]}"
COOKIE_FILE="${2:-/tmp/x_cookie/cookie_full.txt}"

if [[ ! -f "$COOKIE_FILE" ]]; then
  echo "cookie 文件不存在: $COOKIE_FILE" >&2
  exit 1
fi

COOKIE="$(cat "$COOKIE_FILE")"
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

URL="https://syndication.twitter.com/srv/timeline-profile/screen-name/${SCREEN}"

HTTP_CODE=$(curl -s --max-time 30 "$URL" \
  -H "Cookie: ${COOKIE}" \
  -H "User-Agent: ${UA}" \
  -H "Referer: https://syndication.twitter.com/" \
  -H "Accept: text/html,application/xhtml+xml" \
  -o /tmp/x_cookie/last_resp.html \
  -w "%{http_code}")

if [[ "$HTTP_CODE" != "200" ]]; then
  echo "HTTP ${HTTP_CODE}（cookie 失效或 IP 不匹配，可能 403）" >&2
  exit 2
fi

python3 - "$SCREEN" << 'PYEOF'
import json, re, sys, datetime

screen = sys.argv[1]
html = open('/tmp/x_cookie/last_resp.html').read()
m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
if not m:
    print(json.dumps({"error": "no __NEXT_DATA__ in response", "url": "syndication"}), file=sys.stderr)
    sys.exit(3)

data = json.loads(m.group(1))
pageProps = data.get('props', {}).get('pageProps', {})
tl = pageProps.get('timeline') or {}
entries = tl.get('entries') or []

tweets = []
for e in entries:
    t = e.get('content', {}).get('tweet')
    if not t:
        continue
    tweets.append({
        'id': t.get('id_str'),
        'created_at': t.get('created_at'),
        'text': t.get('full_text') or t.get('text'),
        'reply': e.get('content', {}).get('tweet', {}).get('in_reply_to_screen_name') is not None,
        'retweets': t.get('retweet_count', 0),
        'likes': t.get('favorite_count', 0),
        'media': [mm.get('media_url_https') for mm in (t.get('entities', {}).get('media') or [])],
        'url': f"https://x.com/{screen}/status/{t.get('id_str')}",
    })

out = {
    'screen_name': screen,
    'fetched_at': datetime.datetime.now().astimezone().isoformat(),
    'count': len(tweets),
    'tweets': tweets,
}
print(json.dumps(out, ensure_ascii=False, indent=2))
PYEOF
