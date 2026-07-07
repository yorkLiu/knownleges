#!/usr/bin/env python3
"""
X/Twitter 推文图片上传到 Telegraph 图床并更新 MD 文件
- 检测 MD 文件中的本地图片路径
- 上传图片到 Telegraph 图床
- 替换 MD 文件中的图片链接为图床 URL
- 仅处理图片，视频保持使用 nitter 链接
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
    video_keywords = ['video', 'amplify_video_thumb']
    return any(keyword in image_path_str for keyword in video_keywords)


def extract_images_from_md(content):
    """
    从 Markdown 内容中提取图片路径
    
    Returns:
        list of dict: 每个元素包含 original_src 和 is_video 字段
    """
    images = []
    
# 匹配 HTML img 标签
    img_pattern = r'<img\s+src=["\']([^\"]+?)["\'][^>]*>'
    matches = re.findall(img_pattern, content)
    
    for src in matches:
        # 只处理本地图片（/images/ 开头）
        if src.startswith('/images/'):
            # 判断是否是视频缩略图
            is_video = is_video_thumbnail(src)
            images.append({
                'original_src': src,
                'is_video': is_video
            })
    
    return images


def update_md_file(md_file_path, dry_run=False):
    """
    更新单个 MD 文件中的图片链接
    
    Args:
        md_file_path: MD 文件路径
        dry_run: 是否仅预览不实际写入
    
    Returns:
        dict: {'total': int, 'uploaded': int, 'skipped_video': int, 'failed': int}
    """
    md_file_path = Path(md_file_path)
    
    if not md_file_path.exists():
        print(f"❌ 文件不存在：{md_file_path}")
        return None
    
    print(f"\n📄 处理文件：{md_file_path.name}")
    
    # 读取文件内容
    with open(md_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取图片
    images = extract_images_from_md(content)
    
    stats = {
        'total': len(images),
        'uploaded': 0,
        'skipped_video': 0,
        'failed': 0
    }
    
    if not images:
        print(f"  ℹ️  没有找到本地图片")
        return stats
    
    print(f"  📊 找到 {len(images)} 张图片")
    
    # 处理每张图片
    for img_info in images:
        original_src = img_info['original_src']
        is_video = img_info['is_video']
        
        # 视频缩略图跳过
        if is_video:
            print(f"  ⏭️  跳过视频缩略图：{original_src}")
            stats['skipped_video'] += 1
            continue
        
        # 构建本地文件路径
        # /images/username/image.jpg → /home/hermes/workspace/knownleges/docs/public/images/username/image.jpg
        local_path = IMAGES_DIR / original_src.replace('/images/', '')
        
        # 上传图片
        telegraph_url = upload_to_telegraph(local_path)
        
        if telegraph_url:
            # 替换 MD 内容中的图片链接
            # 转义特殊字符
            escaped_src = original_src.replace('/', r'\/').replace('"', r'\"')
            old_img_tag = f'<img src="{original_src}"'
            new_img_tag = f'<img src="{telegraph_url}"'
            
            if old_img_tag in content:
                content = content.replace(old_img_tag, new_img_tag)
                stats['uploaded'] += 1
                print(f"  ✅ 已替换：{original_src} → {telegraph_url}")
            else:
                stats['failed'] += 1
                print(f"  ❌ 替换失败（未找到匹配）：{original_src}")
        else:
            stats['failed'] += 1
    
    # 写入文件
    if not dry_run and stats['uploaded'] > 0:
        with open(md_file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"\n✅ 文件已更新")
    elif dry_run:
        print(f"\nℹ️  预览模式，未写入文件")
    
    return stats


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='X/Twitter 推文图片上传到 Telegraph 图床')
    parser.add_argument('md_files', nargs='*', help='MD 文件路径（可多个）')
    parser.add_argument('--dry-run', action='store_true', help='仅预览，不实际上传和写入')
    parser.add_argument('--all', action='store_true', help='处理 OUTPUT_DIR 中所有 MD 文件')
    
    args = parser.parse_args()
    
    md_files = []
    
    if args.all:
        # 处理所有 MD 文件
        md_files = sorted(OUTPUT_DIR.glob('*.md'))
        if not md_files:
            print(f"❌ 在 {OUTPUT_DIR} 中未找到 MD 文件")
            return
    elif args.md_files:
        md_files = [Path(f) for f in args.md_files]
    else:
        print("使用方法：")
        print(f"  {sys.argv[0]} --all                     # 处理所有 MD 文件")
        print(f"  {sys.argv[0]} file1.md file2.md       # 处理指定文件")
        print(f"  {sys.argv[0]} --dry-run --all          # 预览模式")
        return
    
    print(f"🚀 开始处理 {len(md_files)} 个文件")
    print(f"📁 图床地址：{BASE_URL}")
    print(f"📂 图片目录：{IMAGES_DIR}")
    if args.dry_run:
        print(f"⚠️  预览模式，不会实际上传和写入文件")
    
    total_stats = {
        'total': 0,
        'uploaded': 0,
        'skipped_video': 0,
        'failed': 0
    }
    
    for md_file in md_files:
        stats = update_md_file(md_file, dry_run=args.dry_run)
        if stats:
            for key in total_stats:
                total_stats[key] += stats[key]
    
    # 汇总统计
    print(f"\n{'='*60}")
    print(f"📊 汇总统计")
    print(f"{'='*60}")
    print(f"总图片数：{total_stats['total']}")
    print(f"✅ 已上传：{total_stats['uploaded']}")
    print(f"⏭️  跳过视频：{total_stats['skipped_video']}")
    print(f"❌ 失败：{total_stats['failed']}")
    
    if total_stats['failed'] > 0:
        print(f"\n⚠️  有 {total_stats['failed']} 张图片上传失败，请检查网络或文件权限")


if __name__ == '__main__':
    import sys
    main()