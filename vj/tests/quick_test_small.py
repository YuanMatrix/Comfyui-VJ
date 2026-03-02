#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试 - 小帧数
"""

import requests
import time

API_URL = "http://localhost:5002/api"
TASK_ID = "task-1770493016686-4hy69wup8"

def test_generate_video():
    """测试视频生成"""
    
    # 使用已上传的文件
    images = [
        f"{TASK_ID}/11.jpeg",
        f"{TASK_ID}/12.png",
        f"{TASK_ID}/13.jpg",
        f"{TASK_ID}/14.jpg",
        f"{TASK_ID}/image_media_01KGJJJWM38KJ2ZHE682BDTG89.jpg",
        f"{TASK_ID}/image_media_01KGJJJXR7K6DEMV6SAK5G65C9.jpg",
        f"{TASK_ID}/image_media_01KGJJJXYSEP9GNTWX5M3CAAC9.jpg"
    ]
    
    audio_path = f"/Users/coco/coco-code/ComfyUI/input/{TASK_ID}/Max_Richter_-_On_the_Nature_of_Daylight_20260207_033628.mp3"
    
    print("🎬 提交视频生成任务...")
    print(f"  帧数: 96 (测试用)")
    print(f"  分辨率: 384x384")
    print(f"  帧率: 8 fps")
    print(f"  图片数: {len(images)}")
    
    response = requests.post(f"{API_URL}/generate-video", json={
        "audio_path": audio_path,
        "num_frames": 96,
        "width": 384,
        "height": 384,
        "fps": 8,
        "images": images
    })
    
    if response.status_code == 200 or response.status_code == 202:
        result = response.json()
        task_id = result['task_id']
        print(f"\n✅ 任务创建成功: {task_id}")
        
        print(f"\n查看服务器终端日志...")
        
        return task_id
    else:
        print(f"\n❌ 创建任务失败: {response.status_code}")
        print(response.text)
        return None


if __name__ == '__main__':
    test_generate_video()
