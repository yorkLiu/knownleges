#!/usr/bin/env python3
"""
遍历 docs/x_post_data/*.md 里的每条推文，
从"查看原文"URL 中提取 tweet ID，
在 docs/public/images/{user}/ 下查找对应图片，
在"查看原文"链接前插入 <img> 标签。
"""
import re, os
from pathlib import Path

BASE = Path("/home/hermes/workspace/knownleges")
POSTS_DIR = BASE / "docs/x_post_data"
IMGS_DIR = BASE / "docs/public/images"

md_files = sorted(POSTS_DIR.glob("*.md"))
print(f"发现 {len(md_files)} 个 md 文件")

for md_path in md_files:
    if md_path.name == "index.md":
        continue
    print(f"\n处理: {md_path.name}")

    content = md_path.read_text(encoding="utf-8")
    original = content

    m = re.match(r"^([^_]+)_(\d{4})\.md$", md_path.name)
    if not m:
        continue
    username = m.group(1)
    img_user_dir = IMGS_DIR / username

    # 建立 tweet_id -> img_filename 映射
    img_map = {}
    if img_user_dir.is_dir():
        for f in img_user_dir.iterdir():
            # 文件名格式: amplify_video_thumb_{tweet_id}_img_{hash}.jpg
            # tweet_id 是第4段下划线分隔的字段
            parts = f.stem.split('_')  # stem 无扩展版
            if len(parts) >= 4 and parts[0] == 'amplify' and parts[1] == 'video' and parts[2] == 'thumb':
                tweet_id = parts[3]
                img_map[tweet_id] = f.name
            elif len(parts) >= 1:
                # 通用方案：从头找纯数字段
                for p in parts:
                    if p.isdigit() and len(p) >= 10:
                        img_map[p] = f.name
                        break

    print(f"  用户: {username}, 匹配到图片: {len(img_map)}")

    # 按推文块分割处理
    blocks = re.split(r"(?=^## \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", content, flags=re.MULTILINE)
    new_blocks = []

    for block in blocks:
        if not block.strip():
            new_blocks.append(block)
            continue

        # 提取 tweet ID（主推文，非 RT）
        # 主推文的 nitter link 格式: nitter.net/{user}/status/{tweet_id}
        ids = re.findall(r'nitter\.net/([^/]+)/status/(\d+)', block)
        if not ids:
            new_blocks.append(block)
            continue

        # 取主推文 ID（第一个，非 RT）
        user_in_url, tweet_id = ids[0]

        img_file = img_map.get(tweet_id)
        if not img_file:
            new_blocks.append(block)
            continue

        img_rel = f"/images/{username}/{img_file}"
        img_tag = f'\n<img src="{img_rel}" alt="配图" style="max-width:100%;border-radius:8px;margin:12px 0;">\n'

        # 在 "[查看原文]" 前插入图片
        new_block = re.sub(
            r'(\[查看原文\]\(https?://[^\)]+\))',
            img_tag + r'\1',
            block
        )
        if new_block == block:
            # HTML 格式
            new_block = re.sub(
                r'(<a href="https://nitter[^"]+"[^>]*>[^<]*查看原文[^<]*</a>)',
                img_tag + r'\1',
                block
            )

        new_blocks.append(new_block)

    new_content = "".join(new_blocks)

    if new_content != original:
        md_path.write_text(new_content, encoding="utf-8")
        matched = sum(1 for tid in img_map if any(tid in b for b in new_content.split('## ')))
        print(f"  ✅ 已更新")
    else:
        print(f"  — 无变化")

print("\n完成！请运行: cd /home/hermes/workspace/knownleges && npm run build")