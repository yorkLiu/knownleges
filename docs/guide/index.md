---
layout: page
title: 使用指南
---

# 📖 使用指南

## 🎯 系统介绍

knownleges Wiki 是一个基于 VitePress 构建的推文数据归档与检索系统。

## 📁 目录结构

```
knownleges/
├── docs/              # VitePress 文档目录
│   ├── .vitepress/   # 配置文件
│   ├── data/         # 数据索引 
│   └── index.md      # 首页
├── X/
│   └── data/         # 推文数据（Markdown 格式）
│       ├── {user}.md
│       ├── {user}_{year}.md
│       └── images/   # 图片资源
```

## 🔍 搜索功能

1. 点击右上角搜索按钮（或按 `Ctrl+K`）
2. 输入关键词搜索推文内容
3. 支持标题、正文搜索

## 📊 数据说明

- **数据来源**: X/Twitter 推文
- **更新频率**: 每 30 分钟自动更新
- **时区**: GMT+08:00 (北京时间)
- **格式**: Markdown

## 🏷️ 标签系统

（待添加）

## 🚀 本地开发

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建静态文件
npm run build
```

## 📝 Markdown 语法

本系统支持标准 Markdown 语法：

```markdown
# 标题
## 子标题

**粗体** *斜体*

- 列表项 1
- 列表项 2

[链接](https://example.com)

![图片](image.png)
```
