#!/bin/bash
# Cloudflare Pages build script for knownleges
# 使用 Plan B: build_from_data.js 生成 MD → VitePress 构建为静态 HTML

set -e

echo "🚀 Starting knownleges build for Cloudflare Pages..."

# 1. 安装依赖
echo "📦 Installing dependencies..."
npm ci

# 2. 从 data/x_data 生成 VitePress 文档
echo "📝 Building VitePress documents from data..."
node scripts/build_from_data.js

# 3. 使用 VitePress 构建静态站点
echo "🏗️  Building VitePress site..."
BUILD_DIR="$(pwd)/.vitepress/dist"
npx vitepress build docs --outDir "$BUILD_DIR" --dangerously-ignore-all-dead-links

# 4. 验证输出目录
echo "🔍 Verifying output directory..."
if [ -d "$BUILD_DIR" ]; then
    echo "✅ Output directory exists: $BUILD_DIR"
    
    # 清理不需要的大文件
    if [ -f "$BUILD_DIR/posts.json" ]; then
        echo "🧹 Removing large posts.json file..."
        rm -f "$BUILD_DIR/posts.json" "$BUILD_DIR/posts.json.bak"
    fi
    
    # 显示构建结果
    echo "📊 Build output:"
    ls -la "$BUILD_DIR"
else
    echo "❌ Output directory not found: $BUILD_DIR"
    exit 1
fi

echo "✅ Build completed successfully!"
echo "📂 Static files ready in: $BUILD_DIR"
