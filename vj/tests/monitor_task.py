#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控任务并检查视频帧数
"""

import requests
import time
import subprocess
import sys


def check_video_frames(video_path: str) -> int:
    """检查视频的实际帧数"""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'v:0', 
             '-count_packets', '-show_entries', 'stream=nb_read_packets',
             '-of', 'csv=p=0', video_path],
            capture_output=True,
            text=True
        )
        return int(result.stdout.strip())
    except Exception as e:
        print(f"检查视频帧数失败: {e}")
        return -1


def monitor_task(task_id: str):
    """监控任务进度"""
    
    api_url = f"http://localhost:5002/api/tasks/{task_id}"
    last_status = None
    
    print(f"🔍 监控任务: {task_id}\n")
    
    while True:
        try:
            response = requests.get(api_url)
            if response.status_code == 200:
                data = response.json()
                task = data.get('task', {})
                status = task.get('status')
                
                if status != last_status:
                    print(f"[{time.strftime('%H:%M:%S')}] 状态: {status}")
                    last_status = status
                
                if status == 'completed':
                    print(f"\n✅ 任务完成!")
                    
                    # 获取视频路径
                    video_path = task.get('video_path')
                    if video_path:
                        print(f"📹 视频路径: {video_path}")
                        
                        # 检查帧数
                        print(f"\n🔍 检查视频帧数...")
                        frame_count = check_video_frames(video_path)
                        
                        expected_frames = task['params'].get('num_frames', 'N/A')
                        print(f"\n📊 结果:")
                        print(f"  期望帧数: {expected_frames}")
                        print(f"  实际帧数: {frame_count}")
                        
                        if frame_count == expected_frames:
                            print(f"\n✅ 成功! 帧数正确")
                        else:
                            print(f"\n❌ 失败! 帧数不匹配")
                    
                    break
                
                elif status == 'failed':
                    print(f"\n❌ 任务失败:")
                    print(f"  错误: {task.get('error', 'Unknown')}")
                    break
                
                # 每5秒查询一次
                time.sleep(5)
            else:
                print(f"查询失败: {response.status_code}")
                break
        
        except KeyboardInterrupt:
            print(f"\n中断监控")
            break
        except Exception as e:
            print(f"错误: {e}")
            time.sleep(5)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python monitor_task.py <task_id>")
        sys.exit(1)
    
    task_id = sys.argv[1]
    monitor_task(task_id)
