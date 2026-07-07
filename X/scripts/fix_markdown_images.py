#!/usr/bin/env python3
"""
修复 Markdown 格式的图片链接为 Telegraph 图床 URL
"""

import re
import json
import subprocess
from pathlib import Path

BASE_URL = "https://telegraph-image-fork.pages.dev"
UPLOAD_URL = f"{BASE_URL}/upload"
CACHE_FILE = Path('/home/hermes/workspace/knownleges/X/scripts/telegraph_cache.json')

def load_cache():
    if CACHE_FILE.exists():
        try:
            return json.load(open(CACHE_FILE, 'r', encoding='utf-8'))
        except:
            pass
    return {}

def save_cache(cache):
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def upload_to_telegraph(image_path, verbose=True):
    """上传图片到 Telegraph"""
    image_path = Path(image_path).expanduser().absolute()
    
    if not image_path.exists():
        print(f"  ❌ 文件不存在：{image_path}")
        return None
    
    # 检查缓存
    cache = load_cache()
    cache_key = str(image_path)
    if cache_key in cache:
        if verbose:
            print(f"  ♻️  使用缓存：{image_path.name}")
        return cache[cache_key]
    
    if verbose:
        print(f"  📤 正在上传：{image_path.name}...")
    
    try:
        result = subprocess.run([
            'curl', '-s', '-X', 'POST',
            UPLOAD_URL,
            '-F', f'file=@{image_path}',
            '-H', 'User-Agent: Mozilla/5.0',
            '-w', '\n%{http_code}'
        ], capture_output=True, text=True, timeout=60)
        
        lines = result.stdout.strip().split('\n')
        http_code = lines[-1] if lines else '0'
        body = '\n'.join(lines[:-1]) if len(lines) > 1 else ''
        
        if http_code != '200':
            print(f"  ❌ 上传失败，HTTP: {http_code}")
            return None
        
        response_data = json.loads(body)
        if isinstance(response_data, list) and len(response_data) > 0:
            src_path = response_data[0].get('src', '')
            if src_path:
                full_url = f"{BASE_URL}{src_path}"
                if verbose:
                    print(f"  ✅ 上传成功：{full_url}")
                cache[cache_key] = full_url
                save_cache(cache)
                return full_url
    except Exception as e:
        print(f"  ❌ 异常：{e}")
    
    return None

def fix_md_file(md_file_path, verbose=True):
    """修复 MD 文件中的 Markdown 图片语法"""
    md_file = Path(md_file_path)
    
    if not md_file.exists():
        print(f"❌ 文件不存在：{md_file}")
        return
    
    print(f"\n📄 处理文件：{md_file.name}")
    
    content = md_file.read_text(encoding='utf-8')
    
    # 匹配 Markdown 图片语法
    md_img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    matches = list(re.finditer(md_img_pattern, content))
    
    if not matches:
        print(f"  ℹ️  没有找到 Markdown 格式的图片")
        return
    
    print(f"  📊 找到 {len(matches)} 个 Markdown 格式图片")
    
    replacements = {}
    stats = {'uploaded': 0, 'failed': 0, 'cache': 0}
    
    for match in matches:
        alt_text = match.group(1)
        img_path = match.group(2)
        
        # 只处理本地路径
        if 'public/images' in img_path or img_path.startswith('../'):
            # 转换为绝对路径
            local_path = Path('/home/hermes/workspace/knownleges/docs') / img_path.replace('../public/', 'public/')
            
            # 上传
            telegraph_url = upload_to_telegraph(local_path, verbose=verbose)
            
            if telegraph_url:
                # 替换为 HTML img 标签
                new_tag = f'<img src="{telegraph_url}" alt="{alt_text}" style="max-width:100%;border-radius:8px;margin:8px 0;">'
                replacements[match.group(0)] = new_tag
                stats['uploaded'] += 1
            else:
                stats['failed'] += 1
    
    # 执行替换
    for old, new in replacements.items():
        content = content.replace(old, new)
    
    # 写入文件
    md_file.write_text(content, encoding='utf-8')
    
    print(f"\n✅ 文件已更新")
    print(f"   上传成功：{stats['uploaded']} 个")
    print(f"   失败：{stats['failed']} 个")

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("使用方法：python fix_markdown_images.py <md_file>")
        sys.exit(1)
    
    fix_md_file(sys.argv[1])