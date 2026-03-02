#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试文件上传功能
"""

import requests
import os

API_URL = "http://localhost:5002"

def test_upload_image():
    """测试上传图片"""
    print("=" * 60)
    print("📤 测试图片上传")
    print("=" * 60)
    print()
    
    # 使用现有的测试图片
    test_image = "/Users/coco/Desktop/尖叫1.png"
    
    if not os.path.exists(test_image):
        print(f"❌ 测试图片不存在: {test_image}")
        return
    
    print(f"上传文件: {test_image}")
    
    # 方式1: multipart/form-data
    with open(test_image, 'rb') as f:
        files = {'file': f}
        data = {'filename': 'test_upload.jpg'}  # 可选：自定义文件名
        response = requests.post(f'{API_URL}/api/upload-image', files=files, data=data)
    
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    print()


def test_upload_audio():
    """测试上传音频"""
    print("=" * 60)
    print("📤 测试音频上传")
    print("=" * 60)
    print()
    
    # 使用现有的测试音频
    test_audio = "/Users/coco/coco-code/ComfyUI/input/demo3.mp3"
    
    if not os.path.exists(test_audio):
        print(f"❌ 测试音频不存在: {test_audio}")
        return
    
    print(f"上传文件: {test_audio}")
    
    # multipart/form-data
    with open(test_audio, 'rb') as f:
        files = {'file': f}
        data = {'filename': 'test_audio.mp3'}  # 可选
        response = requests.post(f'{API_URL}/api/upload-audio', files=files, data=data)
    
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    print()


def test_upload_base64():
    """测试 Base64 上传"""
    print("=" * 60)
    print("📤 测试 Base64 上传")
    print("=" * 60)
    print()
    
    test_image = "/Users/coco/coco-code/ComfyUI/input/11.jpg"
    
    if not os.path.exists(test_image):
        print(f"❌ 测试图片不存在: {test_image}")
        return
    
    import base64
    
    # 读取文件并编码为 base64
    with open(test_image, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')
    
    print(f"原文件: {test_image}")
    print(f"Base64 长度: {len(image_data)} 字符")
    print()
    
    # 使用 JSON 格式上传
    response = requests.post(f'{API_URL}/api/upload-image', json={
        'filename': 'test_base64.jpg',
        'data': image_data
    })
    
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    print()


def main():
    print("\n🧪 文件上传 API 测试\n")
    
    # 检查服务
    try:
        response = requests.get(f'{API_URL}/health', timeout=3)
        if response.status_code != 200:
            print("❌ API 服务未运行，请先启动: ./vj/start_vj_api.sh")
            return
    except:
        print("❌ 无法连接到 API 服务，请先启动: ./vj/start_vj_api.sh")
        return
    
    # 运行测试
    test_upload_image()
    # test_upload_audio()
    # test_upload_base64()
    
    print("=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
