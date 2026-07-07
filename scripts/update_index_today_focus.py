import re
import json

# 读取今日关注数据
with open('/tmp/today_focus_counts.json', 'r') as f:
    today_counts = json.load(f)

# 读取当前索引文件
with open('/home/hermes/workspace/knownleges/docs/x_post_data/index.md', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if '| 用户 | 推文数 | 图片数 | 视频数 | 最后更新 |' in line:
        # 修改表头
        new_lines.append('| 用户 | 推文数 | 图片数 | 视频数 | 最后更新 | 今日关注 🔥 |\n')
    elif '|------|--------|--------|--------|----------|' in line:
        # 修改分隔行
        new_lines.append('|------|--------|--------|--------|----------|---------------|\n')
    elif line.startswith('| [@'):
        # 提取用户名
        user_match = re.search(r'\[@([^,\]]+)\]', line)
        if user_match:
            username = user_match.group(1)
            count = today_counts.get(username, 0)
            
            # 创建今日关注徽章
            if count > 0:
                badge = f' 🔥 **{count}** '
            else:
                badge = ''
            
            # 添加今日关注列
            line = line.rstrip().rstrip('|') + f' |{badge} |\n'
    new_lines.append(line)

# 写入文件
with open('/home/hermes/workspace/knownleges/docs/x_post_data/index.md', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✅ 已更新 x_post_data/index.md")
print(f"今日关注数据: {today_counts}")