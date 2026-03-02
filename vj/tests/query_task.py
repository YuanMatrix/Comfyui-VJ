#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查询任务详情
"""

import requests
import sys
import json


def query_task(task_id: str):
    """查询任务详情"""
    
    url = f"http://localhost:5002/api/tasks/{task_id}"
    
    print(f"🔍 查询任务: {task_id}")
    print(f"URL: {url}\n")
    
    try:
        response = requests.get(url)
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            task = data.get('task', {})
            
            print("\n" + "=" * 60)
            print("📋 任务详情")
            print("=" * 60)
            print(f"任务ID: {task['task_id']}")
            print(f"状态: {task['status']}")
            print(f"创建时间: {task.get('created_at', 'N/A')}")
            
            if task.get('completed_at'):
                print(f"完成时间: {task['completed_at']}")
            
            print(f"\n📊 参数:")
            params = task.get('params', {})
            print(f"  帧数: {params.get('num_frames', 'N/A')}")
            print(f"  宽度: {params.get('width', 'N/A')}")
            print(f"  高度: {params.get('height', 'N/A')}")
            print(f"  帧率: {params.get('fps', 'N/A')} fps")
            print(f"  音频: {params.get('audio_path', 'N/A')}")
            print(f"  图片数: {len(params.get('images', []))}")
            
            if params.get('images'):
                print(f"\n📸 图片列表:")
                for idx, img in enumerate(params['images'], 1):
                    print(f"  {idx}. {img}")
            
            if task['status'] == 'completed':
                print(f"\n📹 输出文件:")
                for idx, file_info in enumerate(task.get('output_files', []), 1):
                    print(f"  {idx}. {file_info['filename']}")
                    print(f"     路径: {file_info['path']}")
                
                if task.get('video_path'):
                    print(f"\n🎬 主视频路径: {task['video_path']}")
            
            elif task['status'] == 'failed':
                print(f"\n❌ 错误: {task.get('error', 'Unknown error')}")
            
            print(f"\n⏱️  耗时: {task.get('elapsed_seconds', 0)} 秒")
            print("=" * 60)
            
            # 打印完整 JSON
            print(f"\n📄 完整 JSON 响应:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
        else:
            print(f"\n❌ 请求失败:")
            print(response.text)
    
    except Exception as e:
        print(f"\n❌ 查询失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python query_task.py <task_id>")
        print("\n示例:")
        print("  python vj/tests/query_task.py 77ccceb6-8878-4c42-8f04-470ba459007d")
        sys.exit(1)
    
    task_id = sys.argv[1]
    query_task(task_id)
