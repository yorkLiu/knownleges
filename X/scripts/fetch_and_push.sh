#!/bin/bash
# X/Twitter 推文抓取并自动 Git push（仅在有新增时）
# 用法：./fetch_and_push.sh
set -euo pipefail

# 设置工作目录
cd /data/hermes/workspace/knownleges
echo "=========================================="
echo "🚀 X/Twitter 推文抓取 + Git Push (智能)"
echo "=========================================="
echo "📂 工作目录: $(pwd)"
echo "🕐 开始时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 计算当前所有用户的 meta.json 中的 total_tweets 总和
calculate_total_tweets() {
    local data_dir="./data/x_data"
    if [ ! -d "$data_dir" ]; then
        echo "0"
        return 0
    fi
    # 查找所有 meta.json 并累加 total_tweets
    local total=0
    while IFS= read -r file; do
        if [ -f "$file" ]; then
            # 使用 python 读取 JSON（确保兼容性）
            val=$(python3 -c "import json; print(json.load(open('$file')).get('total_tweets', 0))" 2>/dev/null || echo "0")
            total=$((total + val))
        fi
    done < <(find "$data_dir" -type f -name "meta.json" 2>/dev/null)
    echo "$total"
}

PREV_TOTAL=$(calculate_total_tweets)
echo "📊 运行前累计推文总数: $PREV_TOTAL"
echo ""

# 运行爬虫脚本，捕获输出
echo "📥 正在运行 fetch_x_users.py..."
# 脚本运行时间可能较长，设置超时为 20 分钟（1200 秒）
OUTPUT=$(timeout 1200 python3 X/scripts/fetch_x_users.py 2>&1)
RC=${PIPESTATUS[0]}

echo "$OUTPUT"
echo ""

# 处理超时情况
if [ $RC -eq 124 ]; then
    echo "⏰ 脚本执行超时 (20分钟)，将被中断"
    RC=124
fi

if [ $RC -ne 0 ]; then
    echo "❌ 脚本执行失败，退出码: $RC"
    exit $RC
fi

# 计算运行后的总推文数
CURRENT_TOTAL=$(calculate_total_tweets)
echo "📈 运行后累计推文总数: $CURRENT_TOTAL"

# 判断是否有新增
if [ "$CURRENT_TOTAL" -gt "$PREV_TOTAL" ]; then
    ADDED=$((CURRENT_TOTAL - PREV_TOTAL))
    echo "✨ 发现新增推文: $ADDED 条，准备 Git push"
else
    echo "✅ 无新增推文，无需 Git push"
    echo "📊 (总数: $CURRENT_TOTAL, 之前: $PREV_TOTAL)"
    exit 0
fi

# 执行 Git 操作
echo ""
echo "📤 正在推送到 GitHub..."
echo ""

# 查看变更文件
echo "📋 变更文件:"
git status --short
echo ""

# 添加所有变更
echo "➕ git add -A"
git add -A

# 准备提交信息
COMMIT_MSG="auto: X/Twitter 抓取 $(date '+%Y%m%d-%H%M%S') 新增 ${ADDED} 条推文"
echo "📝 git commit -m \"$COMMIT_MSG\""
git commit -m "$COMMIT_MSG"

# 推送
echo "🚀 git push"
git push

echo ""
echo "✅ Git push 完成！"
echo "=========================================="
echo "📊 本次同步完成"
echo "   - 新增推文: $ADDED 条"
echo "   - 查看日志: tail -f X/scripts/fetch_x_users.log"
echo "   - 手动运行: python3 X/scripts/fetch_x_users.py"
echo "=========================================="