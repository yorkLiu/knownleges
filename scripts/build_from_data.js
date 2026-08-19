#!/usr/bin/env node
/**
 * 将 data/x_data 目录下的 MD 文件转换为 VitePress 兼容格式
 * 输出到 docs/x_post_data 目录，供 VitePress 构建使用
 * 
 * 锚点格式：短链形式如 #0602-0216，永久链接使用 {#_0602-0216}
 * 
 * 不依赖 posts.json，直接从 data/x_data/ 读取
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(__dirname, '..');
const dataDir = path.join(projectRoot, 'data', 'x_data');
const outputDir = path.join(projectRoot, 'docs', 'x_post_data');

// 确保输出目录存在
fs.mkdirSync(outputDir, { recursive: true });

// 生成短链 ID (格式：MMDD-HHmmss)，包含秒数以确保唯一性
function generateShortId(dateStr) {
    const match = dateStr.match(/(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})/);
    if (match) {
        const month = match[2];
        const day = match[3];
        const hour = match[4];
        const minute = match[5];
        const second = match[6];
        return `${month}${day}-${hour}${minute}${second}`;
    }
    return dateStr.replace(/[:\s]/g, '-');
}

/**
 * 从原始 MD 文件解析推文
 */
function parseTweetsFromMD(content, username) {
    const tweets = [];
    
    // 按推文标题分割（## 2026-05-27 00:03:13 或 ## 2026-05-27 00:03:13 GMT+08:00）
    // GMT 后缀可选，适配新旧两种格式
    const tweetPattern = /(?=^## \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\sGMT[+-]\d{2}:\d{2})?(?:\s|$))/m;
    const sections = content.split(tweetPattern);
    
    for (const section of sections) {
        const trimmed = section.trim();
        if (!trimmed) continue;
        
        // 提取时间戳
        const timeMatch = trimmed.match(/^## (.+?)\s*$/m);
        if (!timeMatch) continue;
        const timeStr = timeMatch[1].trim();
        
        // 提取标签
        const tags = [];
        const tagMatches = trimmed.matchAll(/tag-badge tag-([^"]+)/g);
        for (const m of tagMatches) {
            tags.push(m[1]);
        }
        if (tags.length === 0) tags.push(''); // 无标签时留空
        
        // 提取图片（从 img 标签），跳过本地路径，只保留外部 URL
        const images = [];
        const seenImages = new Set();
        const imgMatches = trimmed.matchAll(/<img[^>]+src="([^"]+)"[^>]*>/g);
        for (const m of imgMatches) {
            const imgUrl = m[1];
            // 跳过本地路径（以 / 或 ./ 开头的）
            if (!imgUrl || imgUrl.startsWith('/') || imgUrl.startsWith('./')) continue;
            // 只保留外部 URL（http/https 开头）
            if (!imgUrl.startsWith('http')) continue;
            if (!seenImages.has(imgUrl)) {
                seenImages.add(imgUrl);
                images.push(imgUrl);
            }
        }
        
        // 提取链接
        let link = '';
        const linkMatch = trimmed.match(/\[查看原文\]\(([^)]+)\)/);
        if (linkMatch) link = linkMatch[1];
        
        // 提取内容（移除标签和链接行，移除末尾 triple-sep，保留纯文本）
        let tweetContent = trimmed
            .replace(/\n?---\n?$/gm, '') // 移除末尾 triple-sep 分隔符（源文件自带）
            // 移除 frontmatter/header
            .replace(/^#.*$/mg, '') // 移除 ## 时间戳行（后面会单独处理）
            .replace(/<a[^>]+class="tag-badge[^"]*"[^>]*>.*?<\/a>/g, '') // 移除标签链接
            .replace(/<img[^>]+>/g, '') // 移除图片标签
            .replace(/\*\*内容\*\*:?\s*/g, '') // 移除 **内容**: 标记
            .replace(/\[查看原文\]\([^)]+\)/g, '') // 移除链接
            .replace(/\[📖 原文\]\([^)]+\)/g, '')
            .replace(/\[🔗[^\]]+\]\([^)]+\)/g, '')
            .replace(/^\s*$/gm, '') // 移除空行
            .replace(/\n{3,}/g, '\n\n') // 压缩多余空行
            .replace(/</g, '&lt;') // 转义 < 防止被当成 HTML 标签
            .replace(/>/g, '&gt;') // 转义 > 防止被当成 HTML 标签
            .trim();
        
        tweets.push({
            time: timeStr,
            tags,
            dateTag: timeStr.match(/^(\d{4}-\d{2}-\d{2})/)?.[1]?.replace(/-/g, '') || '', // YYYYMMDD
            content: tweetContent,
            images,
            link
        });
    }
    
    return tweets;
}

/**
 * 处理单个用户目录（包含多个每日文件）
 */
function processUserFile(user, userDir) {
    // 读取该用户的所有每日文件
    const mdFiles = fs.readdirSync(userDir)
        .filter(f => f.endsWith('.md'))
        .map(f => path.join(userDir, f));
    
    // 合并所有每日文件的推文
    let allPosts = [];
    mdFiles.forEach(filePath => {
        const content = fs.readFileSync(filePath, 'utf8');
        const posts = parseTweetsFromMD(content, user);
        allPosts = allPosts.concat(posts);
    });
    
    // 按时间倒序
    allPosts.sort((a, b) => new Date(b.time) - new Date(a.time));
    
    const userPosts = allPosts;
    const year = new Date().getFullYear();
    
    // 构建输出内容
    let output = `---
title: "@${user} 推文存档"
date: ${new Date().toISOString().split('T')[0]}
author: "@${user}"
tags: []
---

# @${user}

> 📊 推文存档 - 共 ${userPosts.length} 条推文

---

## 📊 数据概览

`;
    
    // 标签统计
    const tagStats = {};
    userPosts.forEach(post => {
        (post.tags || []).forEach(tag => {
            tagStats[tag] = (tagStats[tag] || 0) + 1;
        });
    });
    
    Object.entries(tagStats).forEach(([tag, count]) => {
        output += `- **${tag}**: ${count} 条\n`;
    });
    output += `\n---\n\n`;
    
    // 按时间显示推文
    const seenIds = new Map(); // 用于检测重复 ID
    userPosts.forEach((post, idx) => {
        const shortId = generateShortId(post.time);
        let anchorId = `_${shortId}`;
        
        // 检查并处理重复 ID
        if (seenIds.has(shortId)) {
            const count = seenIds.get(shortId) + 1;
            seenIds.set(shortId, count);
            anchorId = `_${shortId}-${count}`;
        } else {
            seenIds.set(shortId, 0);
        }
        
        // 格式化时间显示
        const dateObj = new Date(post.time.replace(/\s*GMT[+-]\d{2}:\d{2}/, ' +08:00'));
        const timeDisplay = post.time.replace(' GMT+08:00', '');
        
        output += `## ${timeDisplay}  {#${anchorId}}\n\n`;
        output += `🏷️ ${post.tags.join(' ')}\n\n`;
        output += `${post.content}\n\n`;
        
        // 添加图片
        if (post.images && post.images.length > 0) {
            post.images.forEach((img, i) => {
                output += `![图片 ${i + 1}](${img})\n\n`;
            });
        }
        
        // 添加链接
        if (post.link) {
            output += `[📖 原文](${post.link})\n\n`;
        }
        
        output += `[🔗 #${shortId.replace(/^-/, '')}](#${anchorId})\n\n`;
        output += `---\n\n`;
    });
    
    output += `*最后更新：${new Date().toISOString()}*\n`;
    
    const outputPath = path.join(outputDir, `${user}_${year}.md`);
    fs.writeFileSync(outputPath, output);
    console.log(`✅ 生成: ${user}_${year}.md (${userPosts.length} 条推文, ${userPosts.reduce((s, p) => s + p.images.length, 0)} 张图片)`);
    
    return { user, count: userPosts.length };
}

// 主函数
function main() {
    console.log('🚀 开始从 data/x_data 构建 VitePress 文档...\n');
    
    // 获取所有用户目录
    const users = fs.readdirSync(dataDir).filter(item => {
        const itemPath = path.join(dataDir, item);
        return fs.statSync(itemPath).isDirectory();
    });
    
    console.log(`📁 发现 ${users.length} 个用户: ${users.join(', ')}\n`);
    
    // 第一步：收集所有推文并按日期分组
    const allTweetsByDate = {}; // { '20260602': [{user, post, shortId}, ...] }
    const userStats = {};
    
    users.forEach(user => {
        const userDir = path.join(dataDir, user);
        const mdFiles = fs.readdirSync(userDir).filter(f => f.endsWith('.md')).map(f => path.join(userDir, f));
        
        let userTotal = 0;
        let userTotalImages = 0;
        let todayCount = 0;
        const today = new Date().toISOString().split('T')[0].replace(/-/g, '');
        
        mdFiles.forEach(filePath => {
            const content = fs.readFileSync(filePath, 'utf8');
            const posts = parseTweetsFromMD(content, user);
            
            posts.forEach(post => {
                if (post.dateTag === today) todayCount++;
                if (post.dateTag) {
                    if (!allTweetsByDate[post.dateTag]) {
                        allTweetsByDate[post.dateTag] = [];
                    }
                    const shortId = generateShortId(post.time);
                    allTweetsByDate[post.dateTag].push({
                        user,
                        time: post.time,
                        shortId,
                        anchorId: `_${shortId}`,
                        tags: post.tags,
                        dateTag: post.dateTag,
                        content: post.content,
                        images: post.images,
                        link: post.link
                    });
                }
            });
            
            userTotal += posts.length;
            userTotalImages += posts.reduce((s, p) => s + p.images.length, 0);
        });
        
        userStats[user] = { count: userTotal, images: userTotalImages, today: todayCount };
    });
    
    // 第二步：生成每个用户的页面（按时间倒序，每条推文带日期 tag）
    const year = new Date().getFullYear();
    
    users.forEach(user => {
        const userDir = path.join(dataDir, user);
        const mdFiles = fs.readdirSync(userDir).filter(f => f.endsWith('.md')).map(f => path.join(userDir, f));
        
        let allPosts = [];
        mdFiles.forEach(filePath => {
            const content = fs.readFileSync(filePath, 'utf8');
            const posts = parseTweetsFromMD(content, user);
            allPosts = allPosts.concat(posts);
        });
        
        // 按时间倒序
        allPosts.sort((a, b) => new Date(b.time) - new Date(a.time));
        
        // 收集所有日期 tag
        const allDateTags = [...new Set(allPosts.map(p => p.dateTag).filter(Boolean))].sort().reverse();
        
        // 构建输出内容
        let output = `---\ntitle: "@${user} 推文存档"\ndate: ${new Date().toISOString().split('T')[0]}\nauthor: "@${user}"\ntags: [${allDateTags.map(t => `"${t}"`).join(', ')}]\n---\n\n# @${user}\n\n> 📊 推文存档 - 共 ${allPosts.length} 条推文\n\n---\n\n## 📊 数据概览\n\n`;
        
        // 日期统计
        const dateStats = {};
        allPosts.forEach(post => {
            if (post.dateTag) {
                dateStats[post.dateTag] = (dateStats[post.dateTag] || 0) + 1;
            }
        });
        
        // 按日期排序
        const sortedDates = Object.entries(dateStats).sort((a, b) => b[0].localeCompare(a[0]));
        const displayLimit = 7;
        
        // 显示前7条，其余折叠
        sortedDates.slice(0, displayLimit).forEach(([date, count]) => {
            output += `- **[${date}](./tags/${date}.html)**: ${count} 条\n`;
        });
        
        if (sortedDates.length > displayLimit) {
            output += `\n<details>\n<summary>📋 查看更多 (${sortedDates.length - displayLimit} 个日期)</summary>\n\n`;
            sortedDates.slice(displayLimit).forEach(([date, count]) => {
                output += `- **[${date}](./tags/${date}.html)**: ${count} 条\n`;
            });
            output += `\n</details>\n`;
        }
        output += `\n---\n\n`;
        
        // 按时间显示推文
        const seenIds = new Map(); // 用于检测重复 ID
        allPosts.forEach((post, idx) => {
            const shortId = generateShortId(post.time);
            let anchorId = `_${shortId}`;
            
            // 检查并处理重复 ID
            if (seenIds.has(shortId)) {
                const count = seenIds.get(shortId) + 1;
                seenIds.set(shortId, count);
                anchorId = `_${shortId}-${count}`;
            } else {
                seenIds.set(shortId, 0);
            }
            
            // 格式化时间显示
            const timeDisplay = post.time.replace(' GMT+08:00', '');
            
            output += `## ${timeDisplay}  {#${anchorId}}\n\n`;
            output += `🏷️ **[${post.dateTag}](./tags/${post.dateTag}.html)** ${post.tags.join(' ')}\n\n`;
            output += `${post.content}\n\n`;
            
            // 添加图片
            if (post.images && post.images.length > 0) {
                post.images.forEach((img, i) => {
                    output += `![图片 ${i + 1}](${img})\n\n`;
                });
            }
            
            // 添加链接
            if (post.link) {
                output += `[📖 原文](${post.link})\n\n`;
            }
            
            output += `[🔗 #${shortId.replace(/^-/, '')}](#${anchorId})\n\n`;
            output += `---\n\n`;
        });
        
        output += `*最后更新：${new Date().toISOString()}*\n`;
        
        const outputPath = path.join(outputDir, `${user}_${year}.md`);
        fs.writeFileSync(outputPath, output);
        console.log(`✅ 生成: ${user}_${year}.md (${allPosts.length} 条推文, ${allPosts.reduce((s, p) => s + p.images.length, 0)} 张图片)`);
    });
    
    // 第三步：生成日期 tag 索引页面
    const tagsDir = path.join(outputDir, 'tags');
    fs.mkdirSync(tagsDir, { recursive: true });
    
    // 生成每个日期的聚合页面
    Object.entries(allTweetsByDate)
        .sort((a, b) => b[0].localeCompare(a[0])) // 按日期倒序
        .forEach(([date, tweets]) => {
            // 按用户和时间排序
            tweets.sort((a, b) => new Date(b.time) - new Date(a.time));
            
            let tagPage = `---\ntitle: "${date} 推文存档"\ndate: ${date.slice(0, 4)}-${date.slice(4, 6)}-${date.slice(6, 8)}\ntags: ["${date}"]\n---\n\n# 📅 ${date} 推文存档\n\n> 📊 共 ${tweets.length} 条推文\n\n---\n\n`;
            
            // 按用户分组
            const byUser = {};
            tweets.forEach(t => {
                if (!byUser[t.user]) byUser[t.user] = [];
                byUser[t.user].push(t);
            });
            
            Object.entries(byUser).forEach(([userName, userTweets]) => {
                tagPage += `## [@${userName}](../${userName}_${year}.md)\n\n`;
                userTweets.forEach(t => {
                    const timeDisplay = t.time.replace(' GMT+08:00', '');
                    tagPage += `### ${timeDisplay}\n\n`;
                    tagPage += `${t.content}\n\n`;
                    
                    if (t.images && t.images.length > 0) {
                        t.images.forEach((img, i) => {
                            tagPage += `![图片 ${i + 1}](${img})\n\n`;
                        });
                    }
                    
                    if (t.link) {
                        tagPage += `[📖 原文](${t.link}) | `;
                    }
                    tagPage += `[🔗 #${t.shortId}](../${t.user}_${year}.md#${t.anchorId})\n\n`;
                    tagPage += `---\n\n`;
                });
            });
            
            tagPage += `*生成时间：${new Date().toISOString()}*\n`;
            
            fs.writeFileSync(path.join(tagsDir, `${date}.md`), tagPage);
                    });
    
                console.log(`✅ 生成 ${Object.keys(allTweetsByDate).length} 个日期 tag 页面`);
    
                // 生成 tags 索引页 (x_post_data/tags/index.md)
                let tagsIndex = `---\ntitle: 日期归档\n---\n\n# 📅 日期归档\n\n> 按日期查看所有推文\n\n---\n\n`;
    
                Object.keys(allTweetsByDate)
                    .sort((a, b) => b.localeCompare(a))
                    .forEach(date => {
                        const count = allTweetsByDate[date].length;
                        tagsIndex += `- **[${date}](./${date}.md)**: ${count} 条推文\\n`;
                    });
    
                fs.writeFileSync(path.join(tagsDir, 'index.md'), tagsIndex);
                console.log(`✅ 生成: tags/index.md`);
    
                // 生成根目录的 tags.md（用于 VitePress 的 tags.html 页面）
                let rootTagsMD = `---\ntitle: 🏷️ 推文标签浏览\n---\n\n# 🏷️ 推文标签浏览\n\n> 按日期快速浏览推文内容，点击查看该日期所有用户的推文\n\n## 📅 日期归档\n\n<style>\n.tag-grid {\n display: grid;\n grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));\n gap: 12px;\n margin: 24px 0;\n}\n.tag-card {\n display: flex;\n flex-direction: column;\n align-items: center;\n padding: 16px 12px;\n background: var(--vp-c-bg-soft);\n border: 1px solid var(--vp-c-divider);\n border-radius: 12px;\n text-decoration: none;\n color: var(--vp-c-text-1);\n transition: all 0.25s ease;\n position: relative;\n overflow: hidden;\n}\n.tag-card:hover {\n transform: translateY(-4px);\n border-color: var(--vp-c-brand-1);\n box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);\n}\n.tag-card::before {\n content: '';\n position: absolute;\n top: 0;\n left: 0;\n right: 0;\n height: 3px;\n background: linear-gradient(90deg, var(--vp-c-brand-1), var(--vp-c-brand-2));\n opacity: 0;\n transition: opacity 0.25s;\n}\n.tag-card:hover::before {\n opacity: 1;\n}\n.tag-date {\n font-size: 1.1rem;\n font-weight: 700;
 font-family: ui-monospace, monospace;\n letter-spacing: 0.5px;\n margin-bottom: 8px;\n text-decoration: none !important;\n}\n.tag-count {\n font-size: 0.85rem;\n color: var(--vp-c-text-2);\n background: var(--vp-c-bg);\n padding: 2px 10px;\n border-radius: 10px;\n}\n.tag-hot .tag-count {\n background: linear-gradient(135deg, #ff6b6b, #ee5a5a);\n color: white;\n font-weight: 600;\n}\n.tag-icon {\n font-size: 1.5rem;\n margin-bottom: 6px;\n opacity: 0.8;\n}\n</style>\n\n<div class="tag-grid">\n`;
    
    // 按日期倒序生成标签卡片
    Object.keys(allTweetsByDate)
        .sort((a, b) => b.localeCompare(a))
        .forEach(date => {
            const count = allTweetsByDate[date].length;
            const isHot = count >= 10;
            const icon = isHot ? '🔥' : '📅';
            rootTagsMD += `<a href="/x_post_data/tags/${date}.html" class="tag-card${isHot ? ' tag-hot' : ''}">\n  <span class="tag-icon">${icon}</span>\n  <span class="tag-date">${date.slice(4)}.${date.slice(6)}</span>\n  <span class="tag-count">${count} 条</span>\n</a>\n`;
        });
    
    rootTagsMD += `</div>\n\n---\n\n*📌 最后更新：${new Date().toISOString()} | 共 ${Object.keys(allTweetsByDate).length} 个日期 | 数据来源：Nitter & X/Twitter*\n`;
    
                fs.writeFileSync(path.join(projectRoot, 'docs', 'tags.md'), rootTagsMD);
                console.log(`✅ 生成: docs/tags.md`);
    
    console.log(`🎉 构建完成！共 ${Object.values(userStats).reduce((s, u) => s + u.count, 0)} 条推文`);
    console.log(`📂 输出目录: ${outputDir}`);
    
    // 生成索引页
    let indexContent = `---\ntitle: 推文数据\n---\n\n# 推文数据 | X/Twitter Archive\n\n> 📈 实时更新的金融科技专家观点存档\n\n---\n\n## 📊 数据概览\n\n| 用户 | 推文数 | 今日更新 | 图片数 | 操作 |\n|------|--------|----------|--------|------|\n`;
    
    users.forEach(user => {
        const stats = userStats[user];
        indexContent += `| [@${user}](./${user}_${year}.md) | ${stats.count} | ${stats.today || 0} | ${stats.images} | [查看](./${user}_${year}.md) |\n`;
    });
    
    indexContent += `\n---\n\n## 📅 [日期归档](./tags/index.md)\n\n> 按日期查看所有推文\n\n`;
    
    // 添加最近7天的快速链接
    const recentDates = Object.keys(allTweetsByDate).sort().reverse().slice(0, 7);
    recentDates.forEach(date => {
        const count = allTweetsByDate[date].length;
        indexContent += `- **[${date}](./x_post_data/tags/${date}.html)**: ${count} 条推文\n`;
    });
    
    indexContent += `\n*数据来源：Nitter & X/Twitter*\n`;
    
    fs.writeFileSync(path.join(outputDir, 'index.md'), indexContent);
    console.log(`✅ 生成: index.md`);
}

main();