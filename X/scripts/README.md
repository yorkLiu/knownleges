# X/Twitter 推文爬虫

## 快速开始

```bash
cd /home/hermes/workspace/X/scripts
python3 fetch_x_users.py
```

## 配置说明

配置文件位置: `config.json`

### 添加新用户

编辑 `config.json`，在 `target_users` 中添加新条目：

```json
{
  "target_users": {
    "username": "用户描述",
    "新用户": "用户描述"
  }
}
```

### 配置参数

- **target_users**: X 用户及描述的字典
- **output_dir**: 输出文件的目录路径
- **rss_base_url**: Nitter RSS 基础 URL（默认: https://nitter.net）
- **max_tweets_per_user**: 每个用户最多获取的推文数（默认: 20）

## 自动化运行

Cron 任务 ID: `d5fd4729c90e`
- 每日 09:00 运行一次
- 输出文件更新到: `/home/hermes/workspace/myPrompts/`

## 输出格式

- 每个用户生成 `{username}.md` 文件
- 汇总报告: `INDEX.md`
- 每条推文包含:
  - 发布时间
  - 推文原文
  - 原链接 (Nitter)

## 成本

- ✅ **完全免费** - 无需 API Key
- 基于 Nitter（Twitter 的私有前端）
- 比 Apify 便宜 99.9%
