#!/usr/bin/env python3
"""
把 docs/x_post_data/*.md 中的 <img src="/knownleges/images/..."> 替换回
VitePress 原生 markdown 图片语法 ![](path)，配合 CSS 样式显示。
"""
import re
from pathlib import Path

BASE = Path("/home/hermes/workspace/knownleges")
POSTS_DIR = BASE / "docs/x_post_data"

for md_file in sorted(POSTS_DIR.glob("*.md")):
    if md_file.name == "index.md":
        continue
    content = md_file.read_text(encoding="utf-8")
    original = content

    # <img src="/knownleges/images/{user}/{filename}" alt="配图" style="...">
    # → ![配图](/knownleges/images/{user}/{filename})
    def img_to_markdown(m):
        src = m.group(1)
        # alt 从配图开始
        return f'![配图]({src})'

    new_content = re.sub(
        r'<img src="(/knownleges/images/[^"]+)" alt="配图"[^>]*>',
        img_to_markdown,
        content
    )

    if new_content != original:
        md_file.write_text(new_content, encoding="utf-8")
        replaced = len(re.findall(r'!\[配图\]\(/knownleges/images/', new_content))
        print(f"✅ {md_file.name}: 转换了 {replaced} 张图片")
    else:
        print(f"— {md_file.name}: 无变化")

print("\n完成！运行: cd /home/hermes/workspace/knownleges && npm run build")