#!/usr/bin/env python3
"""
Git 自动监听服务 - 监听 knownleges 目录变动并自动提交到 GitHub
每 30 秒检查一次变动，只有实际改动时才提交并推送
"""

import subprocess
import time
import os
from datetime import datetime
from pathlib import Path

REPO_DIR = Path("/home/hermes/workspace/knownleges")
LOG_FILE = REPO_DIR / ".git-auto-commit.log"
CHECK_INTERVAL = 30  # 检查间隔（秒）
LAST_COMMIT_FILE = REPO_DIR / ".last_commit_hash"

def log(message: str):
    """记录日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}\n"
    print(log_line, end='')
    with open(LOG_FILE, 'a') as f:
        f.write(log_line)

def get_git_status():
    """获取 git 状态（返回是否有改动，排除 .html 文件）"""
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain', '--', ':!*.html'],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            timeout=10
        )
        # 有输出表示有改动
        return bool(result.stdout.strip())
    except Exception as e:
        log(f"获取状态失败：{e}")
        return False

def get_current_commit_hash():
    """获取当前提交哈希"""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout.strip()
    except Exception:
        return ""

def get_last_commit_hash():
    """获取上次提交的哈希"""
    if LAST_COMMIT_FILE.exists():
        return LAST_COMMIT_FILE.read_text().strip()
    return None

def save_last_commit_hash(hash: str):
    """保存当前提交哈希"""
    LAST_COMMIT_FILE.write_text(hash)

def check_and_commit():
    """检查并提交改动 - 只有在实际改动时才提交和推送"""
    # 检查工作目录是否有改动
    has_changes = get_git_status()
    
    if not has_changes:
        # 没有改动，直接返回，不记录日志，不推送
        return False
    
    # 有改动，开始提交
    log("检测到变动，开始提交...")
    
    # 添加所有改动（排除 .html 文件，这些由 generate_user_pages.js 直接生成）
    result = subprocess.run(
        ['git', 'status', '--porcelain', '--', ':!*.html'],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
        timeout=10
    )
    if not result.stdout.strip():
        # .html 之外没有改动，检查是否只有 .html 被改动
        all_result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            timeout=10
        )
        if all_result.stdout.strip():
            # 有改动但都是 .html，忽略（由 generate_user_pages.js 管理）
            return False

    subprocess.run(['git', 'add', '--', ':!*.html'], cwd=REPO_DIR, timeout=30)
    
    # 再次检查是否真的有 staged 的改动
    status_after_add = get_git_status()
    if not status_after_add:
        # add 之后没有改动，说明是误报
        return False
    
    # 提交
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    commit_msg = f"auto: 自动提交 - {timestamp}"
    
    result = subprocess.run(
        ['git', 'commit', '-m', commit_msg],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
        timeout=60
    )
    
    if result.returncode == 0:
        log(f"提交成功：{commit_msg}")
        
        # 推送到远程
        log("推送到远程仓库...")
        push_result = subprocess.run(
            ['git', 'push', 'origin', 'main'],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if push_result.returncode == 0:
            log("✅ 推送成功！")
            # 保存当前提交哈希
            current_hash = get_current_commit_hash()
            save_last_commit_hash(current_hash)
            return True
        else:
            log(f"❌ 推送失败：{push_result.stderr}")
            return False
    else:
        log(f"❌ 提交失败：{result.stderr}")
        return False

def main():
    log("=" * 60)
    log("Git 自动监听服务启动")
    log(f"监听目录：{REPO_DIR}")
    log(f"检查间隔：{CHECK_INTERVAL} 秒")
    log("规则：只有实际改动时才提交和推送")
    log("=" * 60)
    
    # 初始化最后提交哈希
    initial_hash = get_current_commit_hash()
    if initial_hash:
        save_last_commit_hash(initial_hash)
        log(f"初始提交哈希：{initial_hash[:7]}")
    
    while True:
        try:
            check_and_commit()
            time.sleep(CHECK_INTERVAL)
        except KeyboardInterrupt:
            log("\n服务已停止")
            break
        except Exception as e:
            log(f"错误：{e}")
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
