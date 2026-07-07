#!/usr/bin/env python3
"""
Migration script: Split yearly MD files into daily MD files

Before:
  data/x_data/username/username_2026.md  (big file with all tweets)

After:
  data/x_data/username/
  ├── meta.json              # User metadata
  ├── 2026-06-01.md          # Daily files (small)
  ├── 2026-06-02.md
  └── 2026-06-03.md
"""

import re
import json
import shutil
from pathlib import Path
from datetime import datetime

DATA_DIR = Path("/home/hermes/workspace/knownleges/data/x_data")

def parse_tweets_from_yearly_md(content, username):
    """Parse tweets from yearly MD file"""
    tweets = []
    
    # Split by tweet header
    tweet_pattern = r'(?=^## \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} GMT[+-]\d{2}:\d{2})'
    sections = re.split(tweet_pattern, content, flags=re.MULTILINE)
    
    for section in sections:
        section = section.strip()
        if not section:
            continue
        
        # Extract time
        time_match = re.match(r'^## (.+?)\s*$', section, re.MULTILINE)
        if not time_match:
            continue
        time_str = time_match.group(1).strip()
        
        # Parse time object
        try:
            time_clean = re.sub(r'\s*GMT[+-]\d{2}:\d{2}', '', time_str)
            time_obj = datetime.strptime(time_clean, "%Y-%m-%d %H:%M:%S")
        except:
            time_obj = datetime.now()
        
        # Extract tags
        tags = []
        tag_matches = re.findall(r'tag-badge tag-([^"]+)', section)
        tags = tag_matches if tag_matches else ['今日关注']
        
        # Extract content
        content_match = re.search(r'\*\*内容\*\*:\s*\n\n(.+?)(?=\n\n\[查看原文\]|$)', section, re.DOTALL)
        tweet_content = content_match.group(1).strip() if content_match else ""
        
        # Extract images (both local and remote)
        local_images = []
        failed_images = []
        
        # Local images: src="/images/..."
        img_pattern = r'src="(/images/[^"]+)"'
        for match in re.findall(img_pattern, section):
            if match not in local_images:
                local_images.append(match)
        
        # Remote images: src="https://..."
        remote_pattern = r'src="(https://telegraph[^"]+)"'
        for match in re.findall(remote_pattern, section):
            if match not in failed_images:
                failed_images.append(match)
        
        # Extract link
        link_match = re.search(r'\[查看原文\]\(([^)]+)\)', section)
        link = link_match.group(1) if link_match else ""
        
        tweets.append({
            'time': time_str,
            'time_obj': time_obj,
            'tags': tags,
            'content': tweet_content,
            'local_images': local_images,
            'failed_images': failed_images,
            'link': link,
            'user': username
        })
    
    return tweets

def extract_meta_from_yearly_md(content, username):
    """Extract metadata from yearly MD file header"""
    meta = {
        'username': username,
        'description': '',
        'year': datetime.now().year,
        'last_updated': '',
        'total_tweets': 0
    }
    
    # Extract description
    desc_match = re.search(r'\*\*描述\*\*:\s*(.+)', content)
    if desc_match:
        meta['description'] = desc_match.group(1).strip()
    
    # Extract year
    year_match = re.search(r'\*\*年份\*\*:\s*(\d+)', content)
    if year_match:
        meta['year'] = int(year_match.group(1))
    
    # Extract last updated
    updated_match = re.search(r'\*\*最后更新：(.+?)\*\*', content)
    if updated_match:
        meta['last_updated'] = updated_match.group(1).strip()
    
    # Extract total tweets count
    count_match = re.search(r'\*\*本文件共 (\d+) 条推文\*\*', content)
    if count_match:
        meta['total_tweets'] = int(count_match.group(1))
    
    return meta

def save_daily_files(username, tweets, user_dir):
    """Save tweets to daily MD files"""
    # Group tweets by date
    daily_tweets = {}
    for tweet in tweets:
        date_str = tweet['time_obj'].strftime('%Y-%m-%d')
        if date_str not in daily_tweets:
            daily_tweets[date_str] = []
        daily_tweets[date_str].append(tweet)
    
    # Save each day to a separate file
    for date_str, day_tweets in daily_tweets.items():
        # Sort by time (newest first)
        day_tweets.sort(key=lambda x: x['time_obj'], reverse=True)
        
        output_file = user_dir / f"{date_str}.md"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            # Write tweets for this day
            for tweet in day_tweets:
                f.write(f"## {tweet['time']}\n\n")
                
                # Write tags
                tags_str = "  ".join([
                    f'<a href="/tags.html?tag={tag}" class="tag-badge tag-{tag}">🏷️ {tag}</a>'
                    for tag in tweet['tags']
                ])
                if tags_str:
                    f.write(f"{tags_str}\n\n")
                
    content_cleaned = re.sub(r'<img[^>]+>', '', tweet['content'])
    f.write(f"**内容**:\n\n{content_cleaned}\n\n")
                
                # Write local images
                for img_path in tweet.get('local_images', []):
                    f.write(f'<img src="{img_path}" alt="图片" style="max-width:100%;border-radius:8px;margin:8px 0;">\n\n')
                
                # Write remote images
                for img_url in tweet.get('failed_images', []):
                    f.write(f'<img src="{img_url}" alt="图片" style="max-width:100%;border-radius:8px;margin:8px 0;">\n\n')
                
                f.write(f"[查看原文]({tweet['link']})\n\n")
                f.write("---\n\n")
    
    return daily_tweets

def migrate_user(username, user_dir):
    """Migrate a single user's data from yearly to daily files"""
    # Find yearly MD file
    yearly_files = list(user_dir.glob(f"{username}_*.md"))
    
    if not yearly_files:
        print(f"  ⚠️ No yearly file found for {username}")
        return None
    
    yearly_file = yearly_files[0]
    print(f"  📄 Found yearly file: {yearly_file.name}")
    
    # Read yearly file
    content = yearly_file.read_text(encoding='utf-8')
    
    # Extract metadata
    meta = extract_meta_from_yearly_md(content, username)
    print(f"  📊 {meta['total_tweets']} tweets, year {meta['year']}")
    
    # Parse tweets
    tweets = parse_tweets_from_yearly_md(content, username)
    print(f"  🔍 Parsed {len(tweets)} tweets")
    
    # Save meta.json
    meta_file = user_dir / "meta.json"
    with open(meta_file, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"  ✅ Saved meta.json")
    
    # Save daily files
    daily_tweets = save_daily_files(username, tweets, user_dir)
    print(f"  ✅ Saved {len(daily_tweets)} daily files")
    
    # Backup yearly file
    backup_file = yearly_file.with_suffix('.md.bak')
    shutil.move(yearly_file, backup_file)
    print(f"  📦 Backed up yearly file to {backup_file.name}")
    
    return {
        'username': username,
        'total_tweets': len(tweets),
        'daily_files': len(daily_tweets)
    }

def main():
    print("=" * 70)
    print("🔄 Migration: Yearly MD files → Daily MD files")
    print("=" * 70)
    
    # Get all user directories
    user_dirs = [d for d in DATA_DIR.iterdir() if d.is_dir()]
    print(f"\n📁 Found {len(user_dirs)} users\n")
    
    results = []
    for user_dir in sorted(user_dirs):
        username = user_dir.name
        print(f"👤 Migrating @{username}...")
        
        result = migrate_user(username, user_dir)
        if result:
            results.append(result)
    
    print("\n" + "=" * 70)
    print("✅ Migration complete!")
    print("=" * 70)
    
    for r in results:
        print(f"  @{r['username']}: {r['total_tweets']} tweets in {r['daily_files']} daily files")
    
    print("\n⚠️  Note: Yearly .md files have been backed up as .md.bak")
    print("   After verifying the migration, you can delete the .bak files:")
    print("   find data/x_data -name '*.md.bak' -delete")

if __name__ == '__main__':
    main()