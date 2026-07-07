# X/Twitter 推文爬虫部署与架构文档

> **记录版本**: v2026.06.11  
> **维护者**: knownleges  
> **最后更新**: 2026-06-11

---

## 🏗️ 系统架构

### 数据流向
```mermaid
graph LR
    A[Nitter RSS] -->|HTTPS GET| B(fetch_x_users.py)
    B -->|JSON/HTML 解析| C{有新增？}
    C -->|否 | D[静默 [SILENT]]
    C -->|是 | E[下载图片 + Telegraph 上传]
    E --> F[写入 data/x_data/user/YYYY-MM-DD.md]
    F --> G[build_yearly_summary]
    G -->|合并每日文件 | H[docs/x_post_data/user_2026.md]
    G -->|更新统计 | I[docs/x_post_data/index.md]
    H & I --> J[VitePress 网站构建]
    J --> K[GitHub Pages / Vercel]
```

### 目录结构
```bash
/data/hermes/workspace/knownleges/
├── X/
│   └── scripts/
│       ├── fetch_x_users.py      # 主爬虫脚本 (含合并逻辑)
│       ├── config.json           # 配置 (RSS, 用户, 路径)
│       └── telegraph_cache.json  # 图片上传缓存
├── data/
│   └── x_data/                   # 【原始输出】按用户/日期分片
│       ├── elonmusk/
│       │   ├── 2026-06-11.md
│       │   └── meta.json
│       └── ...
├── docs/
│   ├── x_post_data/              # 【网站数据】年度汇总文件
│   │   ├── index.md              # 主页 (自动更新)
│   │   ├── elonmusk_2026.md      # 年度汇总 (自动生成)
│   │   └── ...
│   ├── public/                   # 静态资源
│   │   └── images/               # 图片缓存
│   └── .vitepress/               # VitePress 配置
└── .git-auto-commit.py           # 独立 git 监听服务 (30s 轮询)
```

---

## ⚙️ 核心组件

### 1. 爬虫脚本 (`X/scripts/fetch_x_users.py`)
**功能**:
- 从 Nitter RSS 获取推文。
- 下载图片并**自动上传到 Telegraph 图床** (如果 `TELEGRAPH_ENABLED=True`)。
- 保存每日切片 (`YYYY-MM-DD.md`)。
- **自动合并**当日所有用户的每日切片为**年度汇总文件** (`user_2026.md`)。
- **自动更新** `docs/x_post_data/index.md` 统计表格。

**关键配置**:
```python
# X/scripts/config.json
{
  "rss_base_url": "https://nitter.net",  // 核心：必须指向可用的 Nitter 实例
  "output_dir": "/data/hermes/workspace/knownleges/data/x_data",
  "target_users": { ... }
}
```

### 2. 定时任务 (Cron Job)
**任务 ID**: `33752113-5694-4759-b979-cba9f44e62bd`  
**调度**: 每 30 分钟 (`every 30m`)  
**逻辑**:
1. 运行 `python3 X/scripts/fetch_x_users.py`。
2. **智能判断**:
   - 若输出包含 `"新增 X 条"` (且 X > 0) → 执行 `git add/commit/push`。
   - 若输出为 `"无新推文"` 或 `"新增 0 条"` → **静默** (`[SILENT]`)，不触发 git。
3. 结果交付：本地日志 (`deliver: local`)。

### 3. 独立 Git 监听服务 (备选/冗余)
**文件**: `.git-auto-commit.py`  
**功能**: 独立于 Cron 运行，每 30 秒轮询 `data/x_data` 和 `docs/x_post_data` 变动。
- 检测到非 `.html` 文件变动 → 自动 `git commit`。
- **注意**: 本方案中**不依赖**此服务作为主要提交手段，仅供冗余备份。

---

## 🚀 快速部署指南 (Setup)

如果服务器重置或重新部署，请按以下步骤操作：

### Step 1: 配置环境变量与依赖
```bash
cd /data/hermes/workspace/knownleges

# 安装 Python 依赖 (如果尚未安装)
pip install feedparser requests Pillow psutil
```

### Step 2: 确认配置
编辑 `X/scripts/config.json`:
- 确保 `rss_base_url` 指向 `https://nitter.net` (或可用的镜像)。
- 确保 `output_dir` 为绝对路径 `/data/hermes/workspace/knownleges/data/x_data`。

### Step 3: 注入合并逻辑 (如果脚本被重置)
如果 `fetch_x_users.py` 丢失了 `build_yearly_summary` 功能，运行以下命令注入：
```bash
cd /data/hermes/workspace/knownleges/X/scripts
python3 -c "
import re, json
from pathlib import Path

# 1. 读取脚本
script_path = 'fetch_x_users.py'
content = Path(script_path).read_text()

# 2. 如果函数已存在则跳过
if 'def build_yearly_summary():' in content:
    print('函数已存在，跳过注入')
    exit(0)

# 3. 定义注入代码 (简化版，实际部署建议使用完整文件)
inject_code = '''
def build_yearly_summary():
    print('\\n  🏗️ 正在构建年度汇总文件...')
    docs_dir = Path(__file__).parents[2] / 'docs/x_post_data'
    docs_dir.mkdir(exist_ok=True)
    index_file = docs_dir / 'index.md'
    
    rows = []
    for user, desc in TARGET_USERS.items():
        user_dir = OUTPUT_DIR / user
        if not user_dir.exists(): continue
        
        files = sorted([f for f in user_dir.glob('*.md') if f.name != 'meta.json' and re.match(r'\\d{4}-\\d{2}-\\d{2}', f.stem)])
        if not files: continue
        
        tweets = []
        for f in files:
            txt = f.read_text(encoding='utf-8')
            tweets.extend([s.strip() for s in txt.split('---\\n\\n') if s.strip().startswith('## ')])
        
        if not tweets: continue
        
        year_file = docs_dir / f'{user}_{datetime.now().year}.md'
        year_file.write_text(f'---\\ntitle: \"@{user} 推文存档\"\\n---\\n\\n' + '\\n\\n---\\n\\n'.join(reversed(tweets)))
        
        rows.append(f'|| [@{user}](./{user}_{datetime.now().year}.md) | {len(tweets)} | | | [查看](./{user}_{datetime.now().year}.md) |')
        print(f'    ✅ {user}')
    
    if rows and index_file.exists():
        # 简单替换逻辑 (实际部署需更健壮)
        pass
'''

# 4. 插入到 main() 函数之前
main_pos = content.find('def main():')
if main_pos > 0:
    new_content = content[:main_pos] + inject_code + '\n\n' + content[main_pos:]
    # 5. 在主函数末尾插入调用
    # 找到最后一个 print("=" * 70) 并插入调用
    lines = new_content.split('\n')
    for i in range(len(lines)-1, -1, -1):
        if 'print("=" * 70)' in lines[i] and i < len(lines)-2:
            lines.insert(i+1, '    build_yearly_summary()')
            break
    Path(script_path).write_text('\n'.join(lines))
    print('✅ 注入成功')
"
```
*(注：实际部署建议直接覆盖 `fetch_x_users.py` 文件，或运行一次本文档中的完整 `write_file` 脚本)*

### Step 4: 创建/修复 Cron Job
**推荐方式**: 直接使用 Hermes CLI 或 API 创建，避免手动编辑 JSON。

**命令**:
```bash
# 如果 hermes CLI 可用
/data/hermes/.hermes/hermes-agent/venv/bin/python -m hermes_cli.main cron create \
  --schedule "every 30m" \
  --name "X 推文自动抓取" \
  --profile knownleges \
  --prompt "在 /data/hermes/workspace/knownleges 运行 python3 X/scripts/fetch_x_users.py。检测输出是否有'新增 X 条'，有则 git push，无则 [SILENT]"

# 如果 CLI 不可用，直接编辑 JSON (不推荐，易出错)
# 编辑 /data/hermes/.hermes/cron/jobs.json
```

**关键配置检查**:
- `schedule`: `every 30m`
- `no_agent`: `false` (必须是 Agent 模式以处理逻辑判断)
- `prompt`: 必须包含“检测新增”和“静默”的指令。

### Step 5: 验证运行
```bash
# 1. 手动运行一次测试
cd /data/hermes/workspace/knownleges
python3 X/scripts/fetch_x_users.py

# 2. 检查输出
# - data/x_data/ 下是否有新的 YYYY-MM-DD.md
# - docs/x_post_data/ 下是否有新的 user_2026.md
# - docs/x_post_data/index.md 是否更新

# 3. 检查 Cron Job 状态
hermes cron list  # 或查看 WebUI
```

---

## 🛠️ 故障排除

### 问题 1: `Expecting value: line 1 column 1 (char 0)`
- **原因**: `config.json` 为空或损坏，或 `telegraph_cache.json` 为空/权限错误。
- **解决**:
  ```bash
  cat X/scripts/config.json | jq .  # 验证 JSON 格式
  ls -l X/scripts/telegraph_cache.json
  ```

### 问题 2: 爬取不到数据 (RSS 403/Timeout)
- **原因**: Nitter 实例被封锁。
- **解决**:
  - 检查 `config.json` 中的 `rss_base_url` 是否可访问：`curl -I https://nitter.net/elonmusk/rss`
  - 如果 blocked，更换为其他可用实例 (如 `nitter.privacydev.net`)，**注意**：需确保脚本中的 `feedparser` 能正常解析该实例的 HTML 结构。

### 问题 3: 图片无法显示
- **原因**: Telegraph 图床上传失败。
- **解决**:
  - 检查 `telegraph_cache.json` 是否有新条目。
  - 检查 `docs/public/images/` 权限。
  - 脚本中默认 `TELEGRAPH_ENABLED=True`，若失败会自动降级使用本地路径 `/images/...`。

### 问题 4: 网站不更新
- **原因**: Cron Job 未触发，或合并逻辑失败。
- **解决**:
  - 检查 `docs/x_post_data/` 是否有新文件生成。
  - 检查 `build_yearly_summary()` 日志输出。
  - 手动运行 `python3 X/scripts/fetch_x_users.py` 查看报错。

---

## 📝 维护记录

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-06-11 | v2.0 | **重构**: 修复 `nitter.net` 配置，注入 `build_yearly_summary` 自动合并逻辑，修复 Cron Job 智能推送。 |
| 2026-06-10 | v1.0 | 初始部署 (使用 xcancel.com，存在逻辑缺陷)。 |