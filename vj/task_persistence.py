#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务持久化管理器

负责将任务信息保存到磁盘，并在 API 重启时恢复
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import threading


class TaskPersistenceManager:
    """任务持久化管理器"""
    
    def __init__(self, storage_file: Path):
        """
        初始化管理器
        
        Args:
            storage_file: 任务存储文件路径
        """
        self.storage_file = storage_file
        self.lock = threading.Lock()
        
        # 确保存储目录存在
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
    
    def save_task(self, task_id: str, task_data: Dict) -> bool:
        """
        保存单个任务到磁盘
        
        Args:
            task_id: 任务 ID
            task_data: 任务数据
            
        Returns:
            是否保存成功
        """
        try:
            with self.lock:
                # 读取现有任务
                tasks = self.load_all_tasks()
                
                # 更新任务
                tasks[task_id] = task_data
                
                # 写入文件
                with open(self.storage_file, 'w', encoding='utf-8') as f:
                    json.dump(tasks, f, ensure_ascii=False, indent=2)
                
                return True
        except Exception as e:
            print(f"[ERROR] 保存任务 {task_id} 失败: {e}")
            return False
    
    def load_all_tasks(self) -> Dict[str, Dict]:
        """
        从磁盘加载所有任务
        
        Returns:
            任务字典 {task_id: task_data}
        """
        try:
            if not self.storage_file.exists():
                return {}
            
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                tasks = json.load(f)
                return tasks
        except Exception as e:
            print(f"[ERROR] 加载任务失败: {e}")
            return {}
    
    def load_task(self, task_id: str) -> Optional[Dict]:
        """
        加载单个任务
        
        Args:
            task_id: 任务 ID
            
        Returns:
            任务数据，如果不存在返回 None
        """
        tasks = self.load_all_tasks()
        return tasks.get(task_id)
    
    def delete_task(self, task_id: str) -> bool:
        """
        删除任务
        
        Args:
            task_id: 任务 ID
            
        Returns:
            是否删除成功
        """
        try:
            with self.lock:
                tasks = self.load_all_tasks()
                
                if task_id in tasks:
                    del tasks[task_id]
                    
                    with open(self.storage_file, 'w', encoding='utf-8') as f:
                        json.dump(tasks, f, ensure_ascii=False, indent=2)
                    
                    return True
                
                return False
        except Exception as e:
            print(f"[ERROR] 删除任务 {task_id} 失败: {e}")
            return False
    
    def get_incomplete_tasks(self) -> List[Dict]:
        """
        获取所有未完成的任务（用于恢复）
        
        Returns:
            未完成的任务列表
        """
        tasks = self.load_all_tasks()
        
        incomplete = []
        for task_id, task_data in tasks.items():
            status = task_data.get('status')
            if status in ['queued', 'processing']:
                incomplete.append(task_data)
        
        return incomplete
    
    def cleanup_old_tasks(self, days: int = 7) -> int:
        """
        清理旧任务
        
        Args:
            days: 保留最近几天的任务
            
        Returns:
            清理的任务数量
        """
        try:
            from datetime import timedelta
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with self.lock:
                tasks = self.load_all_tasks()
                original_count = len(tasks)
                
                # 过滤旧任务
                tasks = {
                    task_id: task_data
                    for task_id, task_data in tasks.items()
                    if datetime.fromisoformat(task_data.get('created_at', datetime.now().isoformat())) > cutoff_date
                }
                
                # 保存
                with open(self.storage_file, 'w', encoding='utf-8') as f:
                    json.dump(tasks, f, ensure_ascii=False, indent=2)
                
                cleaned_count = original_count - len(tasks)
                return cleaned_count
        except Exception as e:
            print(f"[ERROR] 清理旧任务失败: {e}")
            return 0
    
    def get_statistics(self) -> Dict:
        """
        获取任务统计信息
        
        Returns:
            统计信息字典
        """
        tasks = self.load_all_tasks()
        
        stats = {
            'total': len(tasks),
            'queued': 0,
            'processing': 0,
            'completed': 0,
            'failed': 0,
            'cancelled': 0
        }
        
        for task_data in tasks.values():
            status = task_data.get('status')
            if status in stats:
                stats[status] += 1
        
        return stats


def recover_task_status(comfyui_url: str, prompt_id: str) -> Optional[Dict]:
    """
    从 ComfyUI 恢复任务状态
    
    Args:
        comfyui_url: ComfyUI 服务地址
        prompt_id: Prompt ID
        
    Returns:
        任务状态信息，如果失败返回 None
    """
    try:
        import requests
        
        # 查询历史记录
        response = requests.get(f"{comfyui_url}/history/{prompt_id}", timeout=5)
        
        if response.status_code != 200:
            return None
        
        history = response.json()
        
        if prompt_id not in history:
            return None
        
        task_info = history[prompt_id]
        
        # 检查是否完成
        if 'outputs' in task_info:
            return {
                'status': 'completed',
                'outputs': task_info['outputs']
            }
        
        # 检查是否出错
        if task_info.get('status', {}).get('status_str') == 'error':
            return {
                'status': 'failed',
                'error': str(task_info.get('status', {}).get('messages', ''))
            }
        
        # 可能还在处理中
        return {
            'status': 'processing'
        }
    
    except Exception as e:
        print(f"[ERROR] 恢复任务状态失败: {e}")
        return None


if __name__ == '__main__':
    # 测试持久化管理器
    storage_file = Path(__file__).parent / "data" / "tasks.json"
    
    manager = TaskPersistenceManager(storage_file)
    
    # 测试保存
    test_task = {
        'task_id': 'test-123',
        'status': 'processing',
        'created_at': datetime.now().isoformat(),
        'params': {'test': 'data'}
    }
    
    print("测试保存任务...")
    manager.save_task('test-123', test_task)
    
    # 测试加载
    print("测试加载任务...")
    loaded = manager.load_task('test-123')
    print(f"加载结果: {loaded}")
    
    # 测试统计
    print("测试统计信息...")
    stats = manager.get_statistics()
    print(f"统计: {stats}")
    
    # 测试获取未完成任务
    print("测试获取未完成任务...")
    incomplete = manager.get_incomplete_tasks()
    print(f"未完成任务数: {len(incomplete)}")
