#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为所有用户 MD 文件的**所有**标题行添加 VitePress 自定义短 ID
格式：## 2026-05-31 14:46:33 GMT+08:00  ->  ## ... {#0531-1446}
"""

import re
import os
import glob

def add_short_anchor_to_line(line):
    """为单行添加短锚点，如果已有 ID 则保持不变"""
    if '{#' in line:
        return line  # 已有 ID，跳过
    
    # 匹配时间戳标题
    match = re.match(r'^(## \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} GMT[+-]\d{2}:\d{2})$', line.strip())
    if match:
        timestamp = match.group(1)
        time_match = re.search(r'(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):\d{2}', timestamp)
        if time_match:
            year, month, day, hour, minute = time_match.groups()
            short_id = f"{month}{day}-{hour}{minute}"
            return f"{timestamp} {{{short_id}}}\n"
    return line

def process_file(filepath):
    """处理单个文件，添加所有缺失的短锚点"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    modified = False
    new_lines = []
    
    for line in lines:
        orig_line = line
        # 检查是否是时间戳标题
        if re.search(r'^## \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} GMT', line):
            if '{#' not in line:
                # 添加短锚点
                time_match = re.search(r'(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):\d{2}', line)
                if time_match:
                    year, month, day, hour, minute = time_match.groups()
                    short_id = f"{month}{day}-{hour}{minute}"
                    line = line.rstrip() + f" {{{short_id}}}\n"
                    modified = True
        new_lines.append(line)
    
    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        return True
    return False

# 处理所有文件
data_dir = '/home/hermes/workspace/knownleges/docs/x_post_data'
count = 0

md_files = glob.glob(os.path.join(data_dir, '*_2026.md'))
for filepath in sorted(md_files):
    filename = os.path.basename(filepath)
    if process_file(filepath):
        count += 1
        print(f"✅ {filename}")
    else:
        print(f"↑ {filename} (已完成)")

print(f"\n✨ 完成：修改 {count} 个文件")
print("💡 下一步：运行 'npm run build' 生成新的 HTML")