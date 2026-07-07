# 🚀 Git 自动提交服务

## 功能说明

自动监听 `knownleges` 仓库的文件变动，并自动提交推送到 GitHub。

## 服务状态

✅ **服务已启动并运行中**

- 检查间隔：30 秒
- 自动提交：开启
- 自动推送：开启

## 使用方法

### 查看服务状态
```bash
./git-auto-commit-service.sh status
```

### 查看日志
```bash
./git-auto-commit-service.sh logs
```

### 重启服务
```bash
./git-auto-commit-service.sh restart
```

### 停止服务
```bash
./git-auto-commit-service.sh stop
```

### 手动启动服务
```bash
./git-auto-commit-service.sh start
```

## 工作原理

1. **后台监听**: Python 脚本每 30 秒检查一次工作目录的 Git 状态
2. **自动检测**: 发现未提交的改动时自动执行 `git add` 和 `git commit`
3. **自动推送**: 提交成功后自动推送到 GitHub 远程仓库
4. **日志记录**: 所有操作记录在 `.git-auto-commit.log` 文件中

## 文件说明

| 文件 | 说明 |
|------|------|
| `.git-auto-commit.py` | 自动提交主程序 |
| `.git-auto-commit.log` | 运行日志 |
| `.git-auto-commit.pid` | 进程 ID 文件 |
| `git-auto-commit-service.sh` | 服务管理脚本 |
| `GIT-AUTO-COMMIT.md` | 说明文档 |

## 注意事项

- 服务会在提交信息前加上 `auto:` 前缀
- 如果推送失败，提交仍会保留在本地
- 日志文件会持续追加，定期清理避免过大
- 确保 Git 认证已正确配置

## 配置

编辑 `.git-auto-commit.py` 可修改：
- `CHECK_INTERVAL`: 检查间隔（默认 30 秒）
- `REPO_DIR`: 监听目录路径
