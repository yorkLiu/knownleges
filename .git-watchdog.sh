#!/bin/bash
# Git 自动监听提交脚本 - 监听 knownleges 目录变动并自动提交到 GitHub
# 使用 inotifywait 监听文件变化

REPO_DIR="/home/hermes/workspace/knownleges"
LOG_FILE="$REPO_DIR/.git-watchdog.log"
CHECK_INTERVAL=5  # 检查间隔（秒）

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log "Git 监听脚本启动..."

cd "$REPO_DIR" || exit 1

# 检查是否有未提交的改动
check_and_commit() {
    if [ -n "$(git status --porcelain)" ]; then
        log "检测到变动，开始提交..."
        git add -A
        git commit -m "auto: 自动提交 - $(date '+%Y-%m-%d %H:%M:%S')"
        if [ $? -eq 0 ]; then
            log "提交成功，推送到远程..."
            git push origin main
            if [ $? -eq 0 ]; then
                log "推送成功！"
            else
                log "推送失败，但提交已保存在本地"
            fi
        else
            log "提交失败（可能没有实际改动）"
        fi
    fi
}

# 初始检查
check_and_commit

# 持续监听（使用 inotifywait 如果可用，否则轮询）
if command -v inotifywait &> /dev/null; then
    log "使用 inotifywait 监听模式"
    while true; do
        inotifywait -r -e modify,create,delete,move --timeout 5 "$REPO_DIR" 2>/dev/null
        # 排除一些不需要监听的文件
        if [ -n "$(git status --porcelain)" ]; then
            check_and_commit
        fi
    done
else
    log "inotifywait 不可用，使用轮询模式（每 30 秒检查一次）"
    while true; do
        sleep 30
        check_and_commit
    done
fi
