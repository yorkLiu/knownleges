#!/usr/bin/env python3
"""
解决重复 ID 问题：把短 ID 升级为 MMDD-HHMM-序号
"""

import re
from collections import defaultdict
import glob
from pathlib import Path

data_dir = '/home/hermes/workspace/knownleges/docs/x_post_data'
counter = defaultdict(lambda: defaultdict(int))  # {文件: {ID: 计数}}

md_files = sorted(Path(data_dir).glob('*_2026.md'))

total = 0

for filepath in md_files:
    print(f"📄 {filepath.name}")
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 找到所有带短 ID 的标题：## ... {#ID}
    lines = []
    modified = False
    
    for match in re.finditer(r'^(## \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} GMT[^}]+\{\#(\d{4}-\d{4})\})', content, re.MULTILINE):
        orig_line = match.group(0)
        base_id = match.group(2)  # 格式：MMDD-HHMM
        
        # 获取唯一配数
        count = counter[filepath.name][base_id]
        unique_id = f"{base_id}-{count+1}" if count > 0 else base_id
        counter[filepath.name][base_id] += 1
        
        # 更新 ID
        new_line = orig_line.replace(f"{{#{base_id}}}", f"{{#{unique_id}}}")
        if new_line != orig_line:
            modified = True
        lines.append((match.start(), new_line))
        print(f"   ID: {base_id} -> {unique_id}")
        total += 1
    
    # 替换内容（倒序替换避免位置错乱）
    if modified:
        for pos, new_line in sorted(lines, reverse=True, key=lambda x: x[0]):
            content = content[:pos] + new_line + content[pos + len(new_line):]
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ 修复重复 ID
")
    else:
        print(f"--------------------------------")

print(f"✨ 完成：处理 {len(md_files)} 个文件，{total} 个锚点")
print("🎯 零重复短 ID！")