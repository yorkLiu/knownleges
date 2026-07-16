#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 Tags 页面 - 提取所有带标签的推文，按标签分类
核心功能：
1. 扫描所有 *_2026.md 文件
2. 提取带 🏷️ 标签的推文
3. 按标签分类，按时间倒序
4. 生成完整的推文内容（非摘要）
5. 自动更新 tags.md
6. 使用 Telegraph CDN 链接处理图片
"""

import os
import re
import json
from datetime import datetime
from pathlib import Path

def extract_tweets_with_tags(md_file_path):
    """从单个 MD 文件中提取带标签的推文"""
    with open(md_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 分割推文（## 时间戳格式，GMT 后缀可选）
    tweets = []
    parts = re.split(r'^(## \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\sGMT[+-]\d{2}:\d{2})?)', content, flags=re.MULTILINE)
    
    current_header = None
    current_content = []
    
    for i, part in enumerate(parts):
        if part.startswith('## '):
            if current_header and current_content:
                tweets.append({
                    'header': current_header,
                    'content': '\n'.join(current_content).strip()
                })
            current_header = part
            current_content = []
        elif current_header is not None:
            current_content.append(part)
    
    # 添加最后一个推文
    if current_header and current_content:
        tweets.append({
            'header': current_header,
            'content': '\n'.join(current_content).strip()
        })
    
    # 筛选带标签的推文
    tagged_tweets = []
    for tweet in tweets:
        # 查找标签
        tag_matches = re.findall(r'<a href="[^"]*\?tag=([^"]+)"[^>]*>🏷️ ([^<]+)</a>', tweet['content'])
        if tag_matches:
            for tag_id, tag_name in tag_matches:
                # 提取用户名（从文件名）
                username = Path(md_file_path).stem.replace('_2026', '')
                
                # 提取时间戳 (完整格式: YYYY-MM-DD HH:MM:SS GMT±HH:MM)
                time_match = re.search(r'## (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\sGMT[+-]\d{2}:\d{2})?)', tweet['header'])
                timestamp = time_match.group(1) if time_match else ''
                
                # 生成档案链接的 ID (VitePress 默认格式：_YYYY-MM-DD-HH-MM-SS-gmt-HH-MM)
                # 例如：_2026-05-31-22-28-49-gmt-08-00
                if timestamp:
                    # 格式：2026-05-31 22:28:49 GMT+08:00 -> _2026-05-31-22-28-49-gmt-08-00
                    date_time = timestamp.replace(' ', '-').replace(':', '-', 2)
                    date_time = date_time.replace('GMT', 'gmt').replace('+', '-')
                    anchor = f"_{date_time}"
                else:
                    anchor = ""
                
                # 获取原文链接
                original_link = ''
                link_match = re.search(r'\[查看原文\]\((https://nitter\.net/[^)]+)\)', tweet['content'])
                if link_match:
                    original_link = link_match.group(1)
                
                tagged_tweets.append({
                    'username': username,
                    'tag_id': tag_id,
                    'tag_name': tag_name,
                    'header': tweet['header'].strip(),
                    'content': tweet['content'].strip(),
                    'timestamp': timestamp,
                    'anchor': anchor,
                    'original_link': original_link
                })
    
    return tagged_tweets

def generate_tags_page(output_file, data_dir):
    """生成 Tags 页面"""
    print("🔍 扫描推文文件...")
    
    all_tagged_tweets = []
    
    # 扫描所有 MD 文件
    for md_file in sorted(os.listdir(data_dir), reverse=True):
        if not md_file.endswith('_2026.md'):
            continue
        
        md_path = os.path.join(data_dir, md_file)
        print(f"  📄 {md_file}")
        
        tweets = extract_tweets_with_tags(md_path)
        all_tagged_tweets.extend(tweets)
    
    print(f"\n📊 共找到 {len(all_tagged_tweets)} 条带标签的推文")
    
    # 按标签分组
    tweets_by_tag = {}
    for tweet in all_tagged_tweets:
        tag_name = tweet['tag_name']
        if tag_name not in tweets_by_tag:
            tweets_by_tag[tag_name] = []
        tweets_by_tag[tag_name].append(tweet)
    
    # 按用户统计
    user_stats = {}
    for tweet in all_tagged_tweets:
        username = tweet['username']
        if username not in user_stats:
            user_stats[username] = 0
        user_stats[username] += 1
    
    print(f"👥 涉及 {len(user_stats)} 个用户")
    for user, count in sorted(user_stats.items(), key=lambda x: x[1], reverse=True):
        print(f"  @{user}: {count} 条")
    
    # 生成 HTML 内容
    print("\n📝 生成页面内容...")
    
    html_parts = [
        '# 🏷️ 推文标签浏览',
        '',
        '> 按标签快速浏览最新推文内容，无摘要，只看完整推文',
        '',
        '## 📊 标签统计',
        '',
        '<div class="tag-stats-buttons" style="gap: 24px; margin: 32px 0;">',
        ''
    ]
    
    # 添加标签按钮（今日关注排第一，其他按数量排序）
    # 先添加今日关注
    if "今日关注" in tweets_by_tag:
        tag_name = "今日关注"
        tag_tweets = tweets_by_tag[tag_name]
        html_parts.append(f'<a href="#{tag_name}" class="tag-btn tag-today">')
        html_parts.append(f'  <span class="tag-name">🔥 今日关注</span>')
        html_parts.append(f'  <span class="tag-count">{len(tag_tweets)} 条</span>')
        html_parts.append('</a>')
        html_parts.append('')
    
    # 再添加其他标签（按数量排序，排除今日关注）
    other_tags = [(k, v) for k, v in tweets_by_tag.items() if k != "今日关注"]
    sorted_others = sorted(other_tags, key=lambda x: len(x[1]), reverse=True)
    for tag_name, tag_tweets in sorted_others:
        emoji = "⭐"
        tag_class = "tag-weekly"
        html_parts.append(f'<a href="#{tag_name}" class="tag-btn {tag_class}">')
        html_parts.append(f'  <span class="tag-name">{emoji} {tag_name}</span>')
        html_parts.append(f'  <span class="tag-count">{len(tag_tweets)} 条</span>')
        html_parts.append('</a>')
        html_parts.append('')
    
    sorted_tags = []
    if "今日关注" in tweets_by_tag:
        sorted_tags.append(("今日关注", tweets_by_tag["今日关注"]))
    sorted_tags.extend(sorted_others)
    
    html_parts.append('</div>')
    html_parts.append('')
    html_parts.append('---')
    html_parts.append('')
    
    # 按标签生成推文列表
    for tag_name, tweets in sorted_tags:
        # 按时间倒序排序
        tweets.sort(key=lambda x: x['timestamp'], reverse=True)
        
        emoji = "🔥" if tag_name == "今日关注" else "⭐"
        html_parts.append(f'## {emoji} {tag_name}')
        html_parts.append('')
        html_parts.append(f'**{len(tweets)} 条推文**  •  按时间倒序排列')
        html_parts.append('')
        
        # 用户统计（按该标签的推文数统计，改成列表格式）
        tag_user_stats = {}
        for tweet in tweets:
            username = tweet['username']
            if username not in tag_user_stats:
                tag_user_stats[username] = 0
            tag_user_stats[username] += 1
        
        html_parts.append('<div class="tag-user-stats">')
        html_parts.append('<strong>📊 用户贡献</strong>')
        html_parts.append('<ul class="user-stats-list">')
        for user, count in sorted(tag_user_stats.items(), key=lambda x: x[1], reverse=True):
            html_parts.append(f'<li><strong>@{user}</strong>: {count} 条推文</li>')
        html_parts.append('</ul>')
        html_parts.append('</div>')
        html_parts.append('')
        
        html_parts.append('---')
        html_parts.append('')
        
        for tweet in tweets:
            # 用户名和时间
            html_parts.append(f"### @{tweet['username']} - {tweet['timestamp']}")
            html_parts.append('')
            
            # 标签样式化
            tag_class = f"tag-{tweet['tag_name']}"
            tag_link = f'/tags.html?tag={tweet["tag_id"]}'
            html_parts.append(f'<a href="{tag_link}" class="tag-badge {tag_class}">🏷️ {tweet["tag_name"]}</a>')
            html_parts.append('')
            
            # 推文内容（完整，非摘要，移除重复标记等）
            content = tweet['content']
            
            # 移除所有标签标记（可能多个，包括前后的换行）
            content = re.sub(r'\s*<a href="[^"]*\\?tag=[^"]+">🏷️ [^<]+</a>\s*', '', content)
            
            # 移除重复的 **内容**: 标记
            content = re.sub(r'\s*\*\*内容\*\*:\s*', '', content)
            
            # 移除 [查看原文](...) 这些内部链接
            content = re.sub(r'\s*\[查看原文\]\([^)]+\)', '', content)
            
            # 移除 {MMDD-HHMM} 这种短锚点遗留
            content = re.sub(r'\s*\{[^}]+\}\s*', '', content)
            
            # 规范化换行
            
            # 规范化换行
            content = re.sub(r'\\\n+', '\n', content)
            
            # 过滤掉视频缩略图及有问题的图片（两种格式）
            # 1. <img> 标签格式 - 过滤掉 amplify_video_thumb, ext_tw_video, video_thumb, 以及包含 format= 的 bad images
            content = re.sub(r'<img[^>]*(?:amplify_video_thumb|ext_tw_video|video_thumb|format3D)[^>]*>', '', content)
            # 2. ![alt](path) 格式
            content = re.sub(r'!\[[^\]]*\]\([^)]*(?:amplify_video_thumb|ext_tw_video|video_thumb|format3D)[^)]*\)', '', content)
            
            # 清理多余空行（最多保留一个空行）
            content = re.sub(r'\n{3,}', '\n\n', content)
            content = re.sub(r'^\s+', '', content, flags=re.MULTILINE)
            content = content.strip()
            
            html_parts.append(content)
            html_parts.append('')
            
            # 操作链接（显示短格式，链接到长 ID）
            links = []
            # 注意：用户档案文件在 x_post_data/ 目录下
            archive_link = f"./x_post_data/{tweet['username']}_2026.html#{tweet['anchor']}" if tweet['anchor'] else "#"
            
            # 链接显示短格式：0531-2228，但指向长 ID：_2026-05-31-22-28-49-gmt-08-00
            if tweet['anchor']:
                # 提取短代码（MMDD-HHMM）
                short_code = ""
                time_match = re.search(r'(\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{2})', tweet['anchor'])
                if time_match:
                    month, day, hour, minute, _ = time_match.groups()
                    short_code = f"{month}{day}-{hour}{minute}"
                
                # 链接显示「#{短代码}」但指向实际长 ID
                link_text = f"#{short_code}" if short_code else "Wiki 原文"
                links.append(f'[📖 {link_text}]({archive_link})')
            else:
                links.append(f'[📖 Wiki 原文]({archive_link})')
            
            html_parts.append(' | '.join(links))
            html_parts.append('')
            
            # 分割线
            html_parts.append('---')
            html_parts.append('')
    
    # 底部信息
    html_parts.extend([
        '',
        '---',
        '',
        f'*最后更新：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | 数据来源：Nitter | 图片 CDN：Telegraph*',
        ''
    ])
    
    # 写入文件
    output_content = '\n'.join(html_parts)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(output_content)
    
    print(f"\n✅ 已生成：{output_file}")
    print(f"📊 总计：{len(all_tagged_tweets)} 条推文，{len(tweets_by_tag)} 个标签")
    
    return len(all_tagged_tweets)

if __name__ == '__main__':
    workspace = '/home/hermes/workspace/knownleges'
    docs_dir = os.path.join(workspace, 'docs/x_post_data')
    output_file = os.path.join(workspace, 'docs/tags.md')
    
    count = generate_tags_page(output_file, docs_dir)
    
    if count == 0:
        print("\n⚠️  未找到带标签的推文！")
        print("请确保推文 MD 文件中有 🏷️ 标签标记")
    else:
        print("\n✨ Tags 页面生成完成！")
        print("下一步：运行 'npm run build' 并部署")
