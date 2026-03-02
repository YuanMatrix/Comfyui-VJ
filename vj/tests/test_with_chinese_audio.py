#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试带中文文件名的音频文件
"""
import requests
import json
import sys
import io
from pathlib import Path

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

# 检查文件是否存在
comfyui_root = Path(__file__).parent.parent.parent
input_dir = comfyui_root / "input"

print("=" * 60)
print("文件检查")
print("=" * 60)
print(f"音频文件路径: {audio_path}")
print(f"完整路径: {input_dir / audio_path}")
print(f"文件存在: {(input_dir / audio_path).exists()}")
print()

for img in images:
    img_path = input_dir / img
    print(f"图片: {img}")
    print(f"  存在: {img_path.exists()}")
print()

# 生成视频请求
generate_data = {
    "audio_path": audio_path,  # 使用相对路径
    "num_frames": 480,
    "width": 200,
    "height": 200,
    "fps": 16,
    "images": images,
}

print("=" * 60)
print("发送请求")
print("=" * 60)
print("请求参数:")
print(json.dumps(generate_data, indent=2, ensure_ascii=False))
print()

try:
    response = requests.post(f"{BASE_URL}/generate-video", json=generate_data)
    
    print(f"响应状态码: {response.status_code}")
    print(f"响应内容:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    
    if response.status_code == 202:
        print("\n✅ 任务已提交成功！")
        result = response.json()
        print(f"任务 ID: {result['task_id']}")
        print(f"查询状态: {BASE_URL}/tasks/{result['task_id']}")
    else:
        print(f"\n❌ 任务提交失败！")
        
except Exception as e:
    print(f"\n❌ 请求失败: {e}")
    import traceback
    traceback.print_exc()
