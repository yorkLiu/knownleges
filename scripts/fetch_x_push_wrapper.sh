#!/bin/bash
# X 推文自动抓取 wrapper（2026-10-24 强化：陈旧锁清理 + 积压数据救援）
# 语义：
#   exit 0 = 抓取成功（无 git 变更 / 已提交推送 / push 失败仅告警，下轮自动补推）
#   exit 1 = 爬虫脚本本身失败（cookie 失效 / 网络 / DNS 等），需人工介入
cd /data/hermes/workspace/knownleges || exit 1

# 1) 运行爬虫
OUTPUT=$(python3 X/scripts/fetch_x_users.py 2>&1)
PY_EXIT=$?
echo "$OUTPUT"
if [ $PY_EXIT -ne 0 ]; then
    echo ""
    echo "--- ❌ 爬虫脚本退出码 $PY_EXIT，跳过 git（下一轮自动重试）---"
    exit 1
fi

# 2) 判断是否需要走 git
NEED_GIT=0
REASON=""
if echo "$OUTPUT" | grep -q "新增 [1-9][0-9]* 条"; then
    NEED_GIT=1
    REASON="检测到新增推文"
fi
# 积压数据救援：即使本轮 0 新增，只要仓库有"数据类"未提交文件（如上一轮 commit
# 被陈旧 git 锁挡住、或 push 失败后数据滞留本地），照样提交+推送，避免数据永久滞留。
# 只盯数据文件（新增每日 md / 新图片 / 每日文件被改动），忽略每轮必变的易变文件
#（meta.json / fetch_stats / telegraph_cache），否则会 30 分钟 commit 一次造成刷屏。
MEANINGFUL=$(git status --porcelain | grep -E "^\?\? (data/x_data|docs/public/images)|^ M data/x_data/" | grep -vE "meta\.json" | wc -l)
if [ $NEED_GIT -eq 0 ] && [ "$MEANINGFUL" -gt 0 ]; then
    NEED_GIT=1
    REASON="存在未提交数据文件（积压数据救援）"
fi
if [ $NEED_GIT -eq 0 ]; then
    echo ""
    echo "--- 无新增推文且无 git 变更，跳过 git 操作 ---"
    exit 0
fi

# 3) 陈旧锁清理：index.lock 滞留 >10 分钟且无活跃 git 进程 = 崩溃残留，安全删除
LOCK=.git/index.lock
if [ -f "$LOCK" ]; then
    age=$(( $(date +%s) - $(stat -c %Y "$LOCK" 2>/dev/null || echo 0) ))
    if [ "$age" -gt 600 ] && ! pgrep -f "git (commit|push|merge|rebase)" >/dev/null; then
        echo "⚠️ 检测到陈旧 git 锁（已存在 ${age}s），清理：$LOCK"
        rm -f "$LOCK"
    fi
fi

echo ""
echo "--- $REASON，执行 git 提交 ---"
if ! git add -A; then
    echo "❌ git add 失败，下轮重试"
    exit 1
fi
if ! git status --porcelain | grep -q "."; then
    echo "无文件变动，跳过 git 提交。"
    exit 0
fi
if ! git commit -m "docs: update tweets $(date +%Y-%m-%d) [$REASON]"; then
    echo "❌ git commit 失败（详见上方输出），下轮重试"
    exit 1
fi

# 4) push 重试 3 次（GitHub 瞬时故障/限流常见；失败不拖垮任务，本地已 commit，下轮补推）
PUSH_OK=0
for i in 1 2 3; do
    if git push origin main 2>&1; then
        PUSH_OK=1
        break
    fi
    echo "⚠️ git push 第 $i 次失败，5s 后重试..."
    sleep 5
done
if [ $PUSH_OK -eq 1 ]; then
    echo "Git 提交完成！"
else
    echo "⚠️ git push 三次重试均失败：本地已 commit，下一轮自动补推，数据不会丢失"
fi
exit 0
