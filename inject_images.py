#!/usr/bin/env python3
"""
从 X/data/*.md 提取图片引用 → 按 tweet ID 注入到 docs/x_post_data/*.md
"""
import re
from pathlib import Path
from urllib.parse import unquote

BASE      = Path("/home/hermes/workspace/knownleges")
XDATA_DIR = BASE / "X/data"
POSTS_DIR = BASE / "docs/x_post_data"
IMGS_DIR  = BASE / "docs/public/images"

def resolve_xdata_img(raw_path, username):
    """
    X/data 图片路径 → 实际下载的文件路径
    amplify_video_thumb:  images/{user}/amplify_video_thumb/{tweet_id}/img/{hash}.{ext}
                          → amplify_video_thumb_{tweet_id}_img_{hash}.{ext}
    media:                images/{user}/media/{hash}.{ext}
                          → media_{hash}.{ext}
    """
    decoded = unquote(raw_path)
    parts = decoded.split('/')

    if len(parts) == 6 and parts[2] == 'amplify_video_thumb':
        # amplify_video_thumb/{tweet_id}/img/{hash}.{ext}
        tweet_id = parts[3]
        hash_ext = parts[5]
        fname = f'amplify_video_thumb_{tweet_id}_img_{hash_ext}'
    elif len(parts) == 3:
        # media/{hash}.{ext}  → media_{hash}.{ext}
        hash_ext = parts[2]
        fname = f'media_{hash_ext}'
    else:
        return None

    img_path = IMGS_DIR / username / fname
    if img_path.exists():
        return f"/images/{username}/{fname}"
    return None

# 扫描所有 X/data md 文件
total_injected = 0
for src_md in sorted(XDATA_DIR.glob("*.md")):
    if src_md.name == "index.md":
        continue
    m = re.match(r"^([^_]+)_\d{4}\.md$", src_md.name)
    if not m:
        continue
    username = m.group(1)
    dst_md   = POSTS_DIR / src_md.name
    if not dst_md.exists():
        print(f"⚠️  跳过（目标不存在）: {dst_md}")
        continue

    src_txt = src_md.read_text(encoding="utf-8")
    dst_txt = dst_md.read_text(encoding="utf-8")

    # 从 X/data 提取 tweet_id → img tags
    blocks = re.split(r"(?=^## \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", src_txt, flags=re.MULTILINE)
    img_map = {}
    for block in blocks:
        if not block.strip():
            continue
        ids = re.findall(r'nitter\.net/([^/]+)/status/(\d+)', block)
        if not ids:
            continue
        tweet_id = ids[0][1]
        raw_imgs = re.findall(r'!\[.*?\]\(([^)]+)\)', block)
        if not raw_imgs:
            continue
        tags = []
        for raw in raw_imgs:
            url = resolve_xdata_img(raw, username)
            if url:
                tags.append(f'<img src="{url}" alt="配图" style="max-width:100%;border-radius:8px;margin:12px 0;">')
        if tags:
            img_map[tweet_id] = '\n' + '\n'.join(tags) + '\n'

    print(f"{username}: X/data 有 {len(img_map)} 条有图片，", end="")

    # 注入到 docs/x_post_data
    dst_blocks = re.split(r"(?=^## \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", dst_txt, flags=re.MULTILINE)
    new_blocks = []
    injected = 0
    for block in dst_blocks:
        if not block.strip():
            new_blocks.append(block)
            continue
        ids = re.findall(r'nitter\.net/([^/]+)/status/(\d+)', block)
        if not ids:
            new_blocks.append(block)
            continue
        tweet_id = ids[0][1]
        img_tag  = img_map.get(tweet_id)
        if img_tag:
            # Skip if this block already has an <img> tag (prevents duplication on re-runs)
            if '<img ' in block:
                new_blocks.append(block)
                continue
            lines = block.split('\n')
            new_lines = []
            done = False
            for l in lines:
                new_lines.append(l)
                if re.match(r'\[查看原文\]|<a href="https://nitter', l) and not done:
                    new_lines.append(img_tag)
                    done = True
                    injected += 1
            new_blocks.append('\n'.join(new_lines))
        else:
            new_blocks.append(block)

    new_txt = '\n'.join(new_blocks)
    if new_txt != dst_txt:
        dst_md.write_text(new_txt, encoding="utf-8")
        total_injected += injected
        print(f"注入 {injected} 张 ✅")
    else:
        print(f"无匹配（可能推文 ID 不一致）")

print(f"\n总计注入: {total_injected} 张图片")
print("运行构建: cd /home/hermes/workspace/knownleges && npm run build")