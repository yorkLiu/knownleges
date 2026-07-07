# X/Twitter 推文抓取定时任务

## 任务配置

- **任务名称**: X-Twitter 推文抓取
- **任务 ID**: `f3e26a556a27`
- **执行频率**: 每 30 分钟执行一次 (`*/30 * * * *`)
- **脚本路径**: `/home/hermes/workspace/knownleges/X/scripts/fetch_x_users.py`
- **日志文件**: `/home/hermes/workspace/knownleges/X/scripts/fetch_x_users.log`
- **交付方式**: local (结果保存在本地)

## 在 Hermes WebUI 中查看

1. 使用 `/cronjob` 命令查看和管理定时任务
2. 找到任务 `X-Twitter 推文抓取` (ID: `f3e26a556a27`)
3. 可以手动触发运行、暂停或修改任务

## 命令行管理

```bash
# 查看所有定时任务
cronjob action='list'

# 立即运行任务
cronjob action='run' job_id='f3e26a556a27'

# 暂停任务
cronjob action='pause' job_id='f3e26a556a27'

# 恢复任务
cronjob action='resume' job_id='f3e26a556a27'
```

## 查看日志

```bash
# 查看最新日志
tail -50 /home/hermes/workspace/knownleges/X/scripts/fetch_x_users.log

# 实时监控日志
tail -f /home/hermes/workspace/knownleges/X/scripts/fetch_x_users.log
```

## 手动执行

```bash
cd /home/hermes/workspace/knownleges/X/scripts
python3 fetch_x_users.py
```

## 配置用户

编辑 `config.json` 文件可修改要抓取的用户列表：

```json
{
  "target_users": {
    "JonathanDi3614": "A 股第一猛庄",
    "xiaomustock": "川沐｜Trumoo🐮",
    "elonmusk": "Elon Musk",
    "karpathy": "Andrej Karpathy",
    "paulg": "Paul Graham (YC 创始人)"
  },
  "output_dir": "../data",
  "rss_base_url": "https://nitter.net",
  "max_tweets_per_user": 20
}
```

## 输出目录

- **数据文件**: `/home/hermes/workspace/knownleges/X/data/`
- **图片目录**: `/home/hermes/workspace/knownleges/X/data/images/`
- **汇总报告**: `/home/hermes/workspace/knownleges/X/data/INDEX.md`

## 注意事项

1. 确保网络连接正常（需要访问 Nitter RSS）
2. 日志文件会持续增长，建议定期清理
3. 图片会自动下载到本地，注意磁盘空间
4. 每 30 分钟执行一次，避免设置过短时间间隔
