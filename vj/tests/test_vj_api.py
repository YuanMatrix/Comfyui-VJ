#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 VJ 视频生成 API
"""

import requests
import json
import time
from pathlib import Path

# API 配置
API_URL = "http://localhost:5002"

def test_health():
    """测试健康检查"""
    print("=" * 60)
    print("🏥 测试健康检查")
    print("=" * 60)
    
    response = requests.get(f"{API_URL}/health")
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()


def test_generate_video():
    """测试视频生成"""
    print("=" * 60)
    print("🎬 测试视频生成")
    print("=" * 60)
    
    # 准备请求数据
    request_data = {
        "audio_path": "demo3.mp3",  # 相对于 input/ 目录
        "num_frames": 50,
        "width": 200,
        "height": 200,
        "fps": 16,
        "images": ["11.jpg", "12.jpg", "13.jpg", "14.jpg"]
    }
    
    print(f"请求参数:")
    print(json.dumps(request_data, indent=2, ensure_ascii=False))
    print()
    
    # 发送请求
    print("📤 发送请求...")
    response = requests.post(
        f"{API_URL}/api/generate-video",
        json=request_data
    )
    
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
    print()
    
    if not result.get('success'):
        print("❌ 视频生成失败")
        return None
    
    task_id = result.get('task_id')
    print(f"✅ 任务已提交: {task_id}")
    print()
    
    return task_id


def test_task_status(task_id: str, wait_for_completion: bool = True):
    """测试任务状态查询"""
    print("=" * 60)
    print("📊 查询任务状态")
    print("=" * 60)
    
    last_status = None
    
    while True:
        response = requests.get(f"{API_URL}/api/tasks/{task_id}")
        result = response.json()
        
        if result.get('success'):
            task = result['task']
            status = task['status']
            
            # 只在状态变化时打印
            if status != last_status:
                print(f"\n[{time.strftime('%H:%M:%S')}] 状态: {status}")
                print(f"  参数: {task['params']}")
                print(f"  已耗时: {task.get('elapsed_seconds', 0)} 秒")
                
                if status == 'processing':
                    print(f"  ComfyUI 任务ID: {task.get('prompt_id')}")
                
                last_status = status
            else:
                # 同一状态，只打印进度点
                print(".", end="", flush=True)
            
            # 检查是否完成
            if status in ['completed', 'failed', 'cancelled']:
                print()
                
                if status == 'completed':
                    print("\n✅ 任务完成！")
                    
                    # 显示视频绝对路径（新增）
                    if task.get('video_path'):
                        print(f"\n📹 视频路径:")
                        print(f"   {task['video_path']}")
                    
                    # 显示详细输出文件
                    print(f"\n📁 输出文件:")
                    for i, file in enumerate(task.get('output_files', [])):
                        print(f"  [{i}] {file['filename']}")
                        print(f"      路径: {file['path']}")
                    
                    # 如果有多个视频
                    if task.get('video_paths') and len(task['video_paths']) > 1:
                        print(f"\n📹 所有视频路径:")
                        for i, path in enumerate(task['video_paths']):
                            print(f"  [{i}] {path}")
                
                elif status == 'failed':
                    print(f"\n❌ 任务失败: {task.get('error')}")
                else:
                    print(f"\n⚠️  任务已取消")
                
                return task
            
            if not wait_for_completion:
                return task
        
        else:
            print(f"❌ 查询失败: {result.get('error')}")
            return None
        
        # 等待后重试
        time.sleep(3)


def test_download_video(task_id: str):
    """测试视频下载"""
    print("=" * 60)
    print("📥 测试视频下载")
    print("=" * 60)
    
    response = requests.get(f"{API_URL}/api/tasks/{task_id}/download")
    
    if response.status_code == 200:
        # 保存文件
        output_path = Path(__file__).parent / f"test_output_{task_id[:8]}.mp4"
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        print(f"✅ 视频已下载到: {output_path}")
        print(f"文件大小: {len(response.content) / 1024 / 1024:.2f} MB")
    else:
        print(f"❌ 下载失败:")
        print(response.text)


def test_list_tasks():
    """测试任务列表"""
    print("=" * 60)
    print("📋 测试任务列表")
    print("=" * 60)
    
    response = requests.get(f"{API_URL}/api/tasks")
    result = response.json()
    
    if result.get('success'):
        tasks = result['tasks']
        print(f"共有 {result['total']} 个任务:\n")
        
        for task in tasks:
            print(f"  [{task['task_id'][:8]}...] {task['status']}")
            print(f"    创建时间: {task['created_at']}")
            print(f"    参数: 帧数={task['params']['num_frames']}, "
                  f"尺寸={task['params']['width']}x{task['params']['height']}, "
                  f"FPS={task['params']['fps']}")
            print()


def main():
    """主测试流程"""
    print("\n🎬 VJ 视频生成 API 测试")
    print("=" * 60)
    print()
    
    try:
        # 1. 健康检查
        test_health()
        
        # 2. 生成视频
        task_id = test_generate_video()
        
        if not task_id:
            print("❌ 任务提交失败，停止测试")
            return
        
        # 3. 等待完成
        task = test_task_status(task_id, wait_for_completion=True)
        
        if not task:
            return
        
        # 4. 下载视频（如果成功）
        if task['status'] == 'completed':
            test_download_video(task_id)
        
        print()
        
        # 5. 列出所有任务
        test_list_tasks()
        
        print("=" * 60)
        print("✅ 测试完成！")
        print("=" * 60)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
