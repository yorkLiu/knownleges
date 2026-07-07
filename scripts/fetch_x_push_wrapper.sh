#!/bin/bash
set -e
cd /data/hermes/workspace/knownleges

# 加载 GitHub token 用于 git push
export GITHUB_TOKEN=$(grep "^COPILOT_GITHUB_TOKEN=" ~/.hermes/.env 2>/dev/null | cut -d= -f2 | tr -d '\n\r')
if [ -z "$GITHUB_TOKEN" ]; then
    echo "⚠️ 未找到 GITHUB_TOKEN，跳过 git push"
    GITHUB_TOKEN=""
fi

# 运行爬虫并捕获输出
OUTPUT=$(python3 X/scripts/fetch_x_users.py 2>&1)
RETCODE=$?
echo "$OUTPUT"

# 如果有新增，执行 git 操作
if echo "$OUTPUT" | grep -q "新增 [1-9][0-9]* 条"; then
    echo ""
    echo "=== 新增检测：正在执行 git 提交 ==="
    git add -A
    if git status --porcelain | grep -q "."; then
        git commit -m "docs: update tweets $(date +%Y-%m-%d)"
        if [ -n "$GITHUB_TOKEN" ]; then
            echo "🔑 使用 token 推送..."
            git push "https://x-access-token:${GITHUB_TOKEN}@github.com/yorkliu/knownleges.git" main
        else
            echo "⚠️ 无 token，跳过 git push"
        fi
        echo "Git 提交完成！"
    else
        echo "无文件变动，跳过 git 提交。"
    fi
else
    echo ""
    echo "=== 无新增推文，跳过 git 操作 ==="
fi

exit $RETCODE
