# Git 自动提交服务

## 服务状态

自动监听 `/home/hermes/workspace/knownleges` 目录的文件变动，并自动提交推送到 GitHub。

## 启动方式

### 方式 1：Cron 定时检查（已启用）
每分钟检查一次变动并自动提交。

```bash
crontab -l  # 查看当前配置
```

### 方式 2：后台持续监听（推荐）
```bash
cd /home/hermes/workspace/knownleges
python3 .git-auto-commit.py
```

### 方式 3：使用 systemd 服务
```bash
sudo systemctl start git-auto-commit
```

## 日志文件
- 运行日志：`.git-auto-commit.log`
- 最后提交哈希：`.last_commit_hash`

## 停止服务

如果是 cron 方式：
```bash
crontab -e  # 删除对应的 cron 行
```

如果是后台进程：
```bash
pkill -f git-auto-commit.py
```

## 配置
编辑 `.git-auto-commit.py` 修改：
- `CHECK_INTERVAL`: 检查间隔（默认 30 秒）
- `REPO_DIR`: 监听目录
