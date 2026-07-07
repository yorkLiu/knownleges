#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为所有用户 MD 文件的标题行添加 VitePress 自定义 ID
格式：## 2026-05-31 14:46:33 GMT+08:00  ->  ## ... {#0531-1446}
"""

import re
import os

def add_short_anchor(line):
    """为单行标题添加短锚点，如果已有 ID 则跳过"""
    # 如果已经有 ID，跳过
    if '{#' in line:
        return line
    
    # 匹配时间戳标题
    match = re.match(r'^(## \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} GMT[+-]\d{2}:\d{2})$', line)
    if match:
        timestamp = match.group(1)
        # 提取月日时分
        time_match = re.search(r'(\d{2})-(\d{2}) (\d{2}):(\d{2}):', timestamp)
        if time_match:
            month, day, hour, minute = time_match.groups()
            short_id = f"{month}{day}-{hour}{minute}"
            return f"{line} {{{short_id}}}\n"
    return line

def process_file(filepath):
    """处理单个文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    modified = False
    new_lines = []
    
    for line in lines:
        if line.strip().startswith('## ') and re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', line):
            new_line = add_short_anchor(line)
            if new_line != line:
                modified = True
            new_lines.append(new_line)
        else:
            new_lines.append(line)
    
    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        return True
    return False

# 处理所有文件
data_dir = '/home/hermes/workspace/knownleges/docs/x_post_data'
count = 0

for filename in sorted(os.listdir(data_dir)):
    if filename.endswith('_2026.md'):
        filepath = os.path.join(data_dir, filename)
        if process_file(filepath):
            count += 1
            print(f"✅ {filename}")
        else:
            print(f"↑ {filename} (无需修改)")

print(f"\n✨ 完成：修改 {count} 个文件")
print("💡 下一步：运行 npm run build 生成新的 HTML")