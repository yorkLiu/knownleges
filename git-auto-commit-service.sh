#!/bin/bash
# Git 自动提交服务管理脚本

SERVICE_NAME="git-auto-commit"
SCRIPT_PATH="/home/hermes/workspace/knownleges/.git-auto-commit.py"
LOG_FILE="/home/hermes/workspace/knownleges/.git-auto-commit.log"
PID_FILE="/home/hermes/workspace/knownleges/.git-auto-commit.pid"

case "$1" in
    start)
        echo "启动 $SERVICE_NAME 服务..."
        if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
            echo "服务已在运行中 (PID: $(cat $PID_FILE))"
        else
            cd /home/hermes/workspace/knownleges
            nohup python3 "$SCRIPT_PATH" > "$LOG_FILE" 2>&1 &
            echo $! > "$PID_FILE"
            echo "服务已启动 (PID: $(cat $PID_FILE))"
        fi
        ;;
    stop)
        echo "停止 $SERVICE_NAME 服务..."
        if [ -f "$PID_FILE" ]; then
            kill $(cat "$PID_FILE") 2>/dev/null
            rm -f "$PID_FILE"
            echo "服务已停止"
        else
            pkill -f ".git-auto-commit.py"
            echo "服务已停止"
        fi
        ;;
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
    status)
        if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
            echo "服务运行中 (PID: $(cat $PID_FILE))"
        elif pgrep -f ".git-auto-commit.py" > /dev/null; then
            echo "服务运行中 (PID: $(pgrep -f '.git-auto-commit.py'))"
        else
            echo "服务未运行"
        fi
        ;;
    logs)
        tail -50 "$LOG_FILE"
        ;;
    *)
        echo "用法：$0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
