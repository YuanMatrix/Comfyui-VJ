#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试脚本 - 验证修复后的多图片上传功能
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from vj.upload_utils import BatchUploader

def test_batch_upload():
    """测试批量上传功能"""
    print("🧪 测试批量上传功能\n")
    
    # 创建上传器
    uploader = BatchUploader(base_url="http://localhost:5002/api")
    
    # 准备测试文件（使用现有的测试图片）
    test_dir = Path(__file__).parent.parent.parent / "input" / "test_images"
    
    if not test_dir.exists():
        print(f"❌ 测试图片目录不存在: {test_dir}")
        print("   请先运行: python vj/tests/prepare_test_images.py")
        return
    
    image_files = list(test_dir.glob("*.jpg")) + list(test_dir.glob("*.png"))
    
    if len(image_files) < 4:
        print(f"❌ 测试图片不足 4 张，当前只有 {len(image_files)} 张")
        print("   请先运行: python vj/tests/prepare_test_images.py")
        return
    
    # 只使用前 6 张图片
    test_images = image_files[:6]
    print(f"📋 准备上传 {len(test_images)} 张图片:")
    for img in test_images:
        print(f"   - {img.name}")
    print()
    
    # 测试批量上传
    task_id = "test-batch-upload"
    
    try:
        results = uploader.batch_upload(
            file_paths=[str(img) for img in test_images],
            task_id=task_id,
            file_type='image',
            show_progress=True
        )
        
        print(f"\n📊 上传结果:")
        print(f"   成功: {results['success']}")
        print(f"   任务ID: {results['task_id']}")
        print(f"   总数: {results['total']}")
        print(f"   成功数: {results['success_count']}")
        print(f"   失败数: {results['failed_count']}")
        print(f"   耗时: {results['elapsed_seconds']:.2f}s")
        
        if results['uploaded']:
            print(f"\n✅ 上传成功的文件:")
            for img in results['uploaded']:
                print(f"   - {img['filename']} -> {img['relative_path']}")
        
        if results['failed']:
            print(f"\n❌ 上传失败的文件:")
            for img in results['failed']:
                print(f"   - {img['filename']}: {img['error']}")
        
        return results['success']
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_single_upload():
    """测试单个文件上传"""
    print("\n" + "="*60)
    print("🧪 测试单个文件上传\n")
    
    uploader = BatchUploader(base_url="http://localhost:5002/api")
    
    # 使用第一张测试图片
    test_dir = Path(__file__).parent.parent.parent / "input" / "test_images"
    test_image = next(test_dir.glob("*.jpg"), None) or next(test_dir.glob("*.png"), None)
    
    if not test_image:
        print("❌ 没有找到测试图片")
        return False
    
    print(f"📋 准备上传: {test_image.name}\n")
    
    task_id = "test-single-upload"
    
    try:
        result = uploader.upload_file(
            file_path=str(test_image),
            task_id=task_id,
            file_type='image'
        )
        
        print(f"📊 上传结果:")
        print(f"   成功: {result['success']}")
        
        if result['success']:
            print(f"   文件名: {result['filename']}")
            print(f"   相对路径: {result['relative_path']}")
            print(f"   完整路径: {result['full_path']}")
            print(f"   大小: {result['size']} bytes")
        else:
            print(f"   错误: {result.get('error', 'Unknown error')}")
        
        return result['success']
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("="*60)
    print("🧪 上传功能测试")
    print("="*60)
    
    # 测试单个上传
    single_success = test_single_upload()
    
    # 测试批量上传
    print("\n" + "="*60)
    batch_success = test_batch_upload()
    
    # 总结
    print("\n" + "="*60)
    print("📋 测试总结:")
    print(f"   单文件上传: {'✅ 通过' if single_success else '❌ 失败'}")
    print(f"   批量上传: {'✅ 通过' if batch_success else '❌ 失败'}")
    print("="*60)
