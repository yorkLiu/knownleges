#!/usr/bin/env python3
"""
X/Twitter 推文图片上传到 Telegraph 图床（集成到爬虫脚本）
- 在下载图片后自动上传到 Telegraph 图床
- 缓存已上传的图片 URL，避免重复上传
- 仅处理图片，视频保持使用 nitter 链接

使用方式：
1. 修改 fetch_x_users.py，在 download_image 成功后调用 upload_to_telegraph
2. 或者单独运行此脚本处理现有的 MD 文件：
   python upload_images_integration.py --all
"""

import os
import re
import json
import subprocess
from pathlib import Path
from datetime import datetime
import urllib.request
import urllib.error
import time

# ============ 配置 ============
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
BASE_URL = "https://telegraph-image-fork.pages.dev"
UPLOAD_URL = f"{BASE_URL}/upload"

# MD 文件输出目录
OUTPUT_DIR = Path("/home/hermes/workspace/knownleges/docs/x_post_data")

# 图片存储目录
IMAGES_DIR = Path("/home/hermes/workspace/knownleges/docs/public/images")

# 缓存文件
CACHE_FILE = SCRIPT_DIR / "telegraph_cache.json"


def load_cache():
    """加载上传缓存"""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}


def save_cache(cache):
    """保存上传缓存"""
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def upload_to_telegraph(image_path, verbose=True):
    """
    上传图片到 Telegraph 图床
    
    Args:
        image_path: 本地图片文件绝对路径
        verbose: 是否打印详细日志
    
    Returns:
        成功返回完整的图床 URL，失败返回 None
    """
    image_path = Path(image_path).expanduser().absolute()
    
    if not image_path.exists():
        if verbose:
            print(f"  ❌ 文件不存在：{image_path}")
        return None
    
    if not image_path.is_file():
        if verbose:
            print(f"  ❌ 不是文件：{image_path}")
        return None
    
    # 检查文件扩展名（仅图片）
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
    if image_path.suffix.lower() not in allowed_extensions:
        if verbose:
            print(f"  ⚠️  不是图片文件，跳过：{image_path.suffix}")
        return None
    
    if verbose:
        print(f"  📤 正在上传：{image_path.name}...")
    
    try:
        # 使用 curl 上传
        result = subprocess.run([
            'curl', '-s', '-X', 'POST',
            UPLOAD_URL,
            '-F', f'file=@{image_path}',
            '-H', 'User-Agent: Mozilla/5.0',
            '-w', '\n%{http_code}'
        ], capture_output=True, text=True, timeout=60)
        
        # 解析响应
        lines = result.stdout.strip().split('\n')
        http_code = lines[-1] if lines else '0'
        body = '\n'.join(lines[:-1]) if len(lines) > 1 else ''
        
        if http_code != '200':
            if verbose:
                print(f"  ❌ 上传失败，HTTP 状态码：{http_code}")
            return None
        
        # 解析 JSON 响应
        try:
            response_data = json.loads(body)
            if isinstance(response_data, list) and len(response_data) > 0:
                src_path = response_data[0].get('src', '')
                if src_path:
                    full_url = f"{BASE_URL}{src_path}"
                    if verbose:
                        print(f"  ✅ 上传成功：{full_url}")
                    return full_url
        except json.JSONDecodeError as e:
            if verbose:
                print(f"  ❌ JSON 解析失败：{e}")
            if verbose:
                print(f"     原始响应：{body[:200]}")
        
        return None
        
    except subprocess.TimeoutExpired:
        if verbose:
            print(f"  ❌ 上传超时")
        return None
    except Exception as e:
        if verbose:
            print(f"  ❌ 上传异常：{e}")
        return None


def is_video_thumbnail(image_path):
    """
    判断是否是视频缩略图
    视频缩略图通常包含 'video' 或 'amplify_video_thumb' 等关键词
    """
    image_path_str = str(image_path).lower()
    video_keywords = ['video', 'amplify_video_thumb', 'ext_tw_video_thumb']
    return any(keyword in image_path_str for keyword in video_keywords)


def upload_images_for_md(md_file, use_cache=True, verbose=True):
    """
    为 MD 文件中的所有图片上传到 Telegraph 并更新链接
    
    Args:
        md_file: MD 文件路径
        use_cache: 是否使用缓存
        verbose: 是否打印详细日志
    
    Returns:
        dict: 统计信息
    """
    md_file = Path(md_file)
    
    if not md_file.exists():
        print(f"❌ 文件不存在：{md_file}")
        return None
    
    if verbose:
        print(f"\n📄 处理文件：{md_file.name}")
    
    # 读取文件内容
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 加载缓存
    cache = load_cache() if use_cache else {}
    
    # 统计信息
    stats = {
        'total': 0,
        'from_cache': 0,
        'uploaded': 0,
        'skipped_video': 0,
        'failed': 0
    }
    
    # 提取图片路径
    img_pattern = r'<img\s+src=["\'](/images/[^\s"\']+)["\'][^>]*>'
    matches = re.findall(img_pattern, content)
    
    if not matches:
        if verbose:
            print(f"  ℹ️  没有找到本地图片")
        return stats
    
    stats['total'] = len(matches)
    
    if verbose:
        print(f"  📊 找到 {stats['total']} 张图片")
    
    # 去重处理
    unique_images = set()
    processed_images = {}  # original_src -> telegraph_url
    
    for original_src in matches:
        # 跳过视频缩略图
        if is_video_thumbnail(original_src):
            stats['skipped_video'] += 1
            continue
        
        # 跳过已处理的图片
        if original_src in processed_images:
            continue
        
        unique_images.add(original_src)
        
        # 构建本地文件路径
        local_path = IMAGES_DIR / original_src.replace('/images/', '')
        
        # 检查缓存
        cache_key = str(local_path)
        if use_cache and cache_key in cache:
            telegraph_url = cache[cache_key]
            if verbose:
                print(f"  ♻️  使用缓存：{original_src} → {telegraph_url}")
            processed_images[original_src] = telegraph_url
            stats['from_cache'] += 1
            continue
        
        # 上传图片
        telegraph_url = upload_to_telegraph(local_path, verbose=verbose)
        
        if telegraph_url:
            processed_images[original_src] = telegraph_url
            stats['uploaded'] += 1
            
            # 保存到缓存
            if use_cache:
                cache[cache_key] = telegraph_url
                save_cache(cache)
        else:
            stats['failed'] += 1
    
    # 替换 MD 内容中的所有图片链接
    if processed_images:
        for original_src, telegraph_url in processed_images.items():
            old_img_tag = f'<img src="{original_src}"'
            new_img_tag = f'<img src="{telegraph_url}"'
            content = content.replace(old_img_tag, new_img_tag)
        
        # 写入文件
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        if verbose:
            print(f"\n✅ 文件已更新")
    
    return stats


def main():
    """主函数"""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description='X/Twitter 推文图片上传到 Telegraph 图床')
    parser.add_argument('md_files', nargs='*', help='MD 文件路径（可多个）')
    parser.add_argument('--all', action='store_true', help='处理 OUTPUT_DIR 中所有 MD 文件')
    parser.add_argument('--no-cache', action='store_true', help='不使用缓存')
    parser.add_argument('-q', '--quiet', action='store_true', help='静默模式，减少输出')
    
    args = parser.parse_args()
    
    if not args.md_files and not args.all:
        print("使用方法：")
        print(f"  upload_images_integration.py --all                     # 处理所有 MD 文件")
        print(f"  upload_images_integration.py file1.md file2.md       # 处理指定文件")
        print(f"  upload_images_integration.py --all --no-cache         # 不使用缓存")
        return
    
    md_files = []
    
    if args.all:
        # 处理所有 MD 文件
        md_files = sorted(OUTPUT_DIR.glob('*.md'))
        if not md_files:
            print(f"❌ 在 {OUTPUT_DIR} 中未找到 MD 文件")
            return
    elif args.md_files:
        md_files = [Path(f) for f in args.md_files]
    
    verbose = not args.quiet
    
    print(f"🚀 开始处理 {len(md_files)} 个文件")
    print(f"📁 图床地址：{BASE_URL}")
    print(f"📂 图片目录：{IMAGES_DIR}")
    if not args.no_cache:
        print(f"💾 缓存文件：{CACHE_FILE}")
    
    total_stats = {
        'total': 0,
        'from_cache': 0,
        'uploaded': 0,
        'skipped_video': 0,
        'failed': 0
    }
    
    for md_file in md_files:
        stats = upload_images_for_md(md_file, use_cache=not args.no_cache, verbose=verbose)
        if stats:
            for key in total_stats:
                total_stats[key] += stats[key]
    
    # 汇总统计
    print(f"\n{'='*60}")
    print(f"📊 汇总统计")
    print(f"{'='*60}")
    print(f"总图片数：{total_stats['total']}")
    print(f"♻️  从缓存：{total_stats['from_cache']}")
    print(f"✅ 新上传：{total_stats['uploaded']}")
    print(f"⏭️  跳过视频：{total_stats['skipped_video']}")
    print(f"❌ 失败：{total_stats['failed']}")
    
    if total_stats['failed'] > 0:
        print(f"\n⚠️  有 {total_stats['failed']} 张图片上传失败，请检查网络或文件权限")


if __name__ == '__main__':
    import sys
    main()