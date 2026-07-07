#!/usr/bin/env python3
"""
Telegraph-Image 图床上传脚本
上传本地图片到 Telegraph-Image 图床，返回可用的图片 URL
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Optional

# 图床配置
TELEGRAPH_BASE_URL = "https://telegraph-image-fork.pages.dev"
TELEGRAPH_UPLOAD_URL = f"{TELEGRAPH_BASE_URL}/upload"


def upload_image(file_path, verbose=True):
    """
    上传图片到 Telegraph-Image 图床
    
    Args:
        file_path: 本地图片文件路径
        verbose: 是否打印详细日志
    
    Returns:
        成功返回完整的图片 URL，失败返回 None
    """
    file_path = Path(file_path).expanduser().absolute()
    
    if not file_path.exists():
        if verbose:
            print(f"❌ 文件不存在：{file_path}")
        return None
    
    if not file_path.is_file():
        if verbose:
            print(f"❌ 不是文件：{file_path}")
        return None
    
    # 检查文件扩展名
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
    if file_path.suffix.lower() not in allowed_extensions:
        if verbose:
            print(f"⚠️  不支持的文件类型：{file_path.suffix}")
        return None
    
    if verbose:
        print(f"📤 正在上传：{file_path.name}...")
    
    try:
        # 使用 curl 上传
        result = subprocess.run([
            'curl', '-s', '-X', 'POST',
            TELEGRAPH_UPLOAD_URL,
            '-F', f'file=@{file_path}',
            '-H', 'User-Agent: Mozilla/5.0',
            '-w', '\n%{http_code}'
        ], capture_output=True, text=True, timeout=60)
        
        # 解析响应
        lines = result.stdout.strip().split('\n')
        http_code = lines[-1] if lines else '0'
        body = '\n'.join(lines[:-1]) if len(lines) > 1 else ''
        
        if http_code != '200':
            if verbose:
                print(f"❌ 上传失败，HTTP 状态码：{http_code}")
            return None
        
        # 解析 JSON 响应
        try:
            response_data = json.loads(body)
            if isinstance(response_data, list) and len(response_data) > 0:
                src_path = response_data[0].get('src', '')
                if src_path:
                    # 返回完整的 URL
                    full_url = f"{TELEGRAPH_BASE_URL}{src_path}"
                    if verbose:
                        print(f"✅ 上传成功：{full_url}")
                    return full_url
        except json.JSONDecodeError as e:
            if verbose:
                print(f"❌ JSON 解析失败：{e}")
            if verbose:
                print(f"   原始响应：{body[:200]}")
        
        return None
        
    except subprocess.TimeoutExpired:
        if verbose:
            print(f"❌ 上传超时")
        return None
    except Exception as e:
        if verbose:
            print(f"❌ 上传异常：{e}")
        return None


def upload_and_replace_md_image(md_file, image_path, description="图片"):
    """
    上传图片并生成 Markdown 图片链接
    
    Args:
        md_file: Markdown 文件路径（用于确定相对路径）
        image_path: 本地图片文件路径
        description: 图片描述
    
    Returns:
        成功返回 Markdown 格式的图片链接，失败返回 None
    """
    telegraph_url = upload_image(image_path)
    if not telegraph_url:
        return None
    
    # 生成 Markdown 图片语法
    md_link = f'<img src="{telegraph_url}" alt="{description}" style="max-width:100%;border-radius:8px;margin:8px 0;">'
    return md_link


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法：")
        print(f"  {sys.argv[0]} <图片文件路径>")
        print(f"  {sys.argv[0]} --md <Markdown 文件> <图片文件路径> [图片描述]")
        print("\n示例：")
        print(f"  {sys.argv[0]} /path/to/image.jpg")
        print(f"  {sys.argv[0]} --md /path/to/post.md /path/to/image.jpg '图片描述'")
        sys.exit(1)
    
    if sys.argv[1] == '--md' and len(sys.argv) >= 4:
        md_file = sys.argv[2]
        image_path = sys.argv[3]
        description = sys.argv[4] if len(sys.argv) > 4 else "图片"
        
        md_link = upload_and_replace_md_image(md_file, image_path, description)
        if md_link:
            print(f"\n✅ Markdown 链接：\n{md_link}")
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        image_path = sys.argv[1]
        url = upload_image(image_path)
        if url:
            print(f"\n✅ 图床 URL：{url}")
            sys.exit(0)
        else:
            sys.exit(1)


if __name__ == '__main__':
    main()