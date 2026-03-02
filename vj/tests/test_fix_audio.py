#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的API - 使用task_1770545279069_cc9h1cbmi中的音频文件
"""
import requests
import json
import sys
import io

# 设置 Windows 控制台编码为 UTF-8
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# API 基础 URL
BASE_URL = "http://localhost:5002/api"

# Task ID
task_id = "task_1770545279069_cc9h1cbmi"

# 音频文件（相对路径）
audio_path = f"{task_id}/声纹千年.mp3"

# 图片文件（相对路径）
images = [
    f"{task_id}/11.png",
    f"{task_id}/12.png",
    f"{task_id}/13.png",
    f"{task_id}/14.png",
]

# 生成视频请求
generate_data = {
    "audio_path": audio_path,  # 使用相对路径
    "num_frames": 480,  # 30秒 @ 16fps
    "width": 512,
    "height": 512,
    "fps": 16,
    "images": images,
}

print("=" * 60)
print("🧪 测试修复后的API")
print("=" * 60)
print(f"音频文件: {audio_path}")
print(f"图片数量: {len(images)}")
print(f"帧数: {generate_data['num_frames']}")
print(f"分辨率: {generate_data['width']}x{generate_data['height']}")
print(f"帧率: {generate_data['fps']} fps")
print()

try:
    print("📤 发送生成视频请求...")
    response = requests.post(f"{BASE_URL}/generate-video", json=generate_data)
    
    print(f"响应状态码: {response.status_code}")
    
    if response.status_code == 202:
        result = response.json()
        print("\n✅ 任务已提交成功！")
        print(f"   任务 ID: {result['task_id']}")
        print(f"   状态: {result['status']}")
        print(f"   查询状态: {BASE_URL}/tasks/{result['task_id']}")
        print(f"\n📝 提示: 请查看API服务终端，应该能看到:")
        print(f"   [UPDATE] Node XXX: 音频文件设置为 {audio_path}")
    else:
        print(f"\n❌ 任务提交失败！")
        print(f"响应内容:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        
except Exception as e:
    print(f"\n❌ 请求失败: {e}")
    import traceback
    traceback.print_exc()
