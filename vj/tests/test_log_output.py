#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试改进后的日志输出
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
    "audio_path": audio_path,
    "num_frames": 480,
    "width": 512,
    "height": 512,
    "fps": 16,
    "images": images,
}

print("=" * 80)
print("🧪 测试改进后的日志输出")
print("=" * 80)
print("\n📤 发送生成视频请求...")
print(f"API端点: {BASE_URL}/generate-video")
print("\n📋 请求参数:")
print(json.dumps(generate_data, indent=2, ensure_ascii=False))
print("\n" + "=" * 80)
print("📝 提示: 请查看API服务终端，现在应该能看到:")
print("=" * 80)
print("1. JSON 数据格式化显示（缩进4格）")
print("2. 📋 生成视频参数 区块")
print("3. [UPDATE] Node XXX: 音频文件设置为 ... （这是关键！）")
print("=" * 80)
print()

try:
    response = requests.post(f"{BASE_URL}/generate-video", json=generate_data, timeout=10)
    
    if response.status_code == 202:
        result = response.json()
        print("✅ 任务已提交成功！")
        print(f"   任务 ID: {result['task_id']}")
        print(f"   查询地址: {BASE_URL}/tasks/{result['task_id']}")
    else:
        print(f"❌ 任务提交失败！状态码: {response.status_code}")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        
except requests.exceptions.Timeout:
    print("⏱️  请求超时")
except Exception as e:
    print(f"❌ 请求失败: {e}")
