# 📚 knownleges - 我的知识库

> 精选推文与洞察 · 自动同步更新

---

## 📊 统计概览

| 项目 | 数量 |
|------|------|
| 关注用户 | 5 位 |
| 推文总数 | 99+ 条 |
| 图片数量 | 99+ 张 |
| 更新频率 | 每 30 分钟 |

---

## 👥 关注列表

### 🏷️ A 股
- **@JonathanDi3614** - A 股第一猛庄
  - [查看推文](X/data/JonathanDi3614_2026.md)

### 📈 财经
- **@xiaomustock** - 川沐｜Trumoo
  - [查看推文](X/data/xiaomustock_2026.md)

### 💡 科技
- **@elonmusk** - Elon Musk
  - [查看推文](X/data/elonmusk_2026.md)

### 🤖 AI
- **@karpathy** - Andrej Karpathy
  - [查看推文](X/data/karpathy_2026.md)

### 🚀 创业
- **@paulg** - Paul Graham (YC 创始人)
  - [查看推文](X/data/paulg_2026.md)

---

## 📁 索引与报告

- 📑 [推文总索引](X/data/INDEX.md) - 所有推文的汇总
- 📊 [统计报告](X/stats/) - 抓取统计与数据分析

---

## ⚙️ 系统特性

- ✅ **自动抓取** - 每 30 分钟自动同步最新推文
- ✅ **智能去重** - 只保留新增内容，避免重复
- ✅ **按年存储** - 数据按年份分文件，便于管理
- ✅ **图片本地化** - 所有图片自动下载到本地
- ✅ **统计分析** - 详细的抓取统计报告

---
## 流程
Cron Job (每30分钟)
    ↓
fetch_x_users.py
    ↓
data/x_data/{user}/YYYY-MM-DD.md  (每日小文件)
    ↓
手动: node scripts/build_from_data.js
    ↓
docs/x_post_data/{user}_2026.md  (VitePress 源)
    ↓
手动: npm run build (VitePress)
    ↓
docs/.vitepress/dist/  (静态 HTML)
    ↓
Nginx 服务

--- 

## 🔧 技术栈

- **部署平台**: [Vercel](https://vercel.com)
- **数据源**: X/Twitter (via Nitter RSS)
- **自动化工具**: Hermes Agent
- **更新机制**: Git Auto-Commit

---

*最后更新：2026-05-24*  
*由 [Hermes Agent](https://hermes-agent.nousresearch.com) 自动维护*
# Fix duplicate timestamps
