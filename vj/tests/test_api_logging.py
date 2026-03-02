#!/usr/bin/env python3
"""
测试 API 日志功能
发送一些请求来验证日志输出
"""

import requests
import json

BASE_URL = "http://localhost:5002"

print("=" * 60)
print("测试 API 日志功能")
print("=" * 60)

# 测试 1: 404 错误 - 错误的端点
print("\n1️⃣ 测试 404 错误 - 访问不存在的端点")
print("   请求: POST /api/upload")
response = requests.post(f"{BASE_URL}/api/upload", json={"test": "data"})
print(f"   响应: {response.status_code}")
if response.status_code == 404:
    print(f"   ✅ 正确返回 404")
    print(f"   响应内容: {response.json()}")
else:
    print(f"   ❌ 预期 404，实际 {response.status_code}")

# 测试 2: 正确的端点 - 健康检查
print("\n2️⃣ 测试正确的端点")
print("   请求: GET /health")
response = requests.get(f"{BASE_URL}/health")
print(f"   响应: {response.status_code}")
if response.status_code == 200:
    print(f"   ✅ 服务正常")
    print(f"   响应内容: {response.json()}")
else:
    print(f"   ❌ 服务异常")

# 测试 3: 带参数的请求
print("\n3️⃣ 测试带查询参数的请求")
print("   请求: GET /api/tasks?limit=10&status=completed")
response = requests.get(f"{BASE_URL}/api/tasks", params={"limit": 10, "status": "completed"})
print(f"   响应: {response.status_code}")
print(f"   返回任务数: {len(response.json().get('tasks', []))}")

# 测试 4: 带 JSON 数据的请求
print("\n4️⃣ 测试带 JSON 数据的请求（应该看到日志中的 JSON 数据）")
print("   请求: POST /api/generate-video")
test_data = {
    "audio_path": "test.mp3",
    "num_frames": 100,
    "width": 512,
    "height": 512,
    "fps": 16
}
response = requests.post(f"{BASE_URL}/api/generate-video", json=test_data)
print(f"   响应: {response.status_code}")
if response.status_code != 200:
    error = response.json()
    print(f"   错误: {error.get('error', 'Unknown')}")

print("\n" + "=" * 60)
print("测试完成！请查看 API 服务终端的日志输出")
print("=" * 60)
