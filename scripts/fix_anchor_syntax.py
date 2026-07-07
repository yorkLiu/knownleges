#!/usr/bin/env python3
"""
检查并修复所有 MD 文件的锚点语法
VitePress 正确语法：## 标题 {#custom-id}
"""

import re
import glob
from pathlib import Path

data_dir = '/home/hermes/workspace/knownleges/docs/x_post_data'
md_files = sorted(Path(data_dir).glob('*_2026.md'))

for filepath in md_files:
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    modified = False
    
    for line in lines:
        # 匹配标题行：## 2026-05-31 14:46:33 GMT+08:00
        match = re.match(r'^(## \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} GMT[+-]\d{2}:\d{2})\b', line.strip())
        if match and '{#' not in line:
            timestamp = match.group(1)
            # 提取短 ID: MMDD-HHMM
            time_match = re.search(r'(\d{2})-(\d{2}) (\d{2}):(\d{2}):', timestamp)
            if time_match:
                month, day, hour, minute = time_match.groups()
                short_id = f"{month}{day}-{hour}{minute}"
                # 正确语法：## 标题 {#短ID}
                line = line.rstrip() + f' {{#{short_id}}}\n'
                modified = True
        new_lines.append(line)
    
    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print(f"✅ 修复 {filepath.name}")
    else:
        print(f"↑ {filepath.name} (已正确)")

print("✨ 检查完成")
print("💡 确保 VitePress 正确解析 {#相同行} 语法")