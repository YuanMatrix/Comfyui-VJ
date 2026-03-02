#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
准备测试图片

从现有的 input 目录复制图片，或创建占位符图片用于测试
"""

import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import random


def create_test_image(output_path: Path, text: str, size=(512, 512)):
    """创建一个简单的测试图片"""
    # 生成随机颜色
    bg_color = (
        random.randint(100, 255),
        random.randint(100, 255),
        random.randint(100, 255)
    )
    
    # 创建图片
    img = Image.new('RGB', size, color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # 添加文字
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 60)
    except:
        font = ImageFont.load_default()
    
    # 计算文字位置（居中）
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (size[0] - text_width) / 2
    y = (size[1] - text_height) / 2
    
    # 绘制文字
    draw.text((x, y), text, fill=(255, 255, 255), font=font)
    
    # 保存
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)
    print(f"✅ 创建测试图片: {output_path}")


def prepare_test_images(num_images: int = 10):
    """准备测试图片"""
    
    base_dir = Path(__file__).parent.parent.parent
    input_dir = base_dir / "input"
    test_images_dir = input_dir / "test_images"
    
    print(f"📁 测试图片目录: {test_images_dir}")
    
    # 检查是否已有现成的图片可以复制
    existing_images = list(input_dir.glob("*.jpg")) + list(input_dir.glob("*.png"))
    
    if len(existing_images) >= num_images:
        print(f"\n✅ 找到 {len(existing_images)} 张现有图片，将复制前 {num_images} 张")
        test_images_dir.mkdir(parents=True, exist_ok=True)
        
        for i in range(num_images):
            src = existing_images[i]
            dst = test_images_dir / f"image{i+1}{src.suffix}"
            shutil.copy2(src, dst)
            print(f"   复制: {src.name} -> {dst.name}")
    else:
        print(f"\n⚠️  现有图片不足 {num_images} 张，将创建测试图片")
        
        # 先复制现有的
        copied = 0
        for img in existing_images:
            dst = test_images_dir / f"image{copied+1}{img.suffix}"
            shutil.copy2(img, dst)
            print(f"   复制: {img.name} -> {dst.name}")
            copied += 1
        
        # 创建剩余的
        for i in range(copied, num_images):
            output_path = test_images_dir / f"image{i+1}.jpg"
            create_test_image(output_path, f"Image {i+1}")
    
    print(f"\n✅ 测试图片准备完成! 共 {num_images} 张")
    print(f"   路径: {test_images_dir}")
    
    # 列出所有图片
    print(f"\n📋 图片列表:")
    for img in sorted(test_images_dir.glob("*")):
        if img.suffix.lower() in ['.jpg', '.jpeg', '.png']:
            size = img.stat().st_size / 1024
            print(f"   - {img.name} ({size:.1f} KB)")


if __name__ == '__main__':
    import sys
    
    num_images = 10  # 默认创建 10 张
    
    if len(sys.argv) > 1:
        try:
            num_images = int(sys.argv[1])
            if not (4 <= num_images <= 10):
                print("❌ 数量必须在 4-10 之间")
                sys.exit(1)
        except ValueError:
            print("❌ 请提供有效的数字")
            sys.exit(1)
    
    print("🎨 准备测试图片")
    print("=" * 60)
    prepare_test_images(num_images)
