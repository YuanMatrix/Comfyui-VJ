#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试任务持久化和恢复功能
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from vj.task_persistence import TaskPersistenceManager
from datetime import datetime
import json


def test_persistence():
    """测试持久化功能"""
    
    storage_file = Path(__file__).parent.parent / "data" / "test_tasks.json"
    manager = TaskPersistenceManager(storage_file)
    
    print("=" * 60)
    print("🧪 任务持久化功能测试")
    print("=" * 60)
    print(f"📁 测试文件: {storage_file}\n")
    
    # 1. 保存任务
    print("📝 测试 1: 保存任务")
    print("-" * 60)
    
    test_tasks = {
        "task-completed": {
            "task_id": "task-completed",
            "status": "completed",
            "created_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat(),
            "params": {"test": "data"}
        },
        "task-processing": {
            "task_id": "task-processing",
            "status": "processing",
            "prompt_id": "prompt-123",
            "created_at": datetime.now().isoformat(),
            "params": {"test": "data"}
        },
        "task-queued": {
            "task_id": "task-queued",
            "status": "queued",
            "created_at": datetime.now().isoformat(),
            "params": {"test": "data"}
        },
        "task-failed": {
            "task_id": "task-failed",
            "status": "failed",
            "error": "Test error",
            "created_at": datetime.now().isoformat(),
            "params": {"test": "data"}
        }
    }
    
    for task_id, task_data in test_tasks.items():
        success = manager.save_task(task_id, task_data)
        status_icon = "✅" if success else "❌"
        print(f"  {status_icon} 保存任务: {task_id} ({task_data['status']})")
    
    print()
    
    # 2. 加载所有任务
    print("📂 测试 2: 加载所有任务")
    print("-" * 60)
    
    loaded_tasks = manager.load_all_tasks()
    print(f"  加载了 {len(loaded_tasks)} 个任务:")
    for task_id, task_data in loaded_tasks.items():
        print(f"    - {task_id}: {task_data['status']}")
    
    print()
    
    # 3. 加载单个任务
    print("🔍 测试 3: 加载单个任务")
    print("-" * 60)
    
    task = manager.load_task("task-processing")
    if task:
        print(f"  ✅ 找到任务: task-processing")
        print(f"     状态: {task['status']}")
        print(f"     Prompt ID: {task.get('prompt_id', 'N/A')}")
    else:
        print(f"  ❌ 未找到任务")
    
    print()
    
    # 4. 获取未完成任务
    print("⏳ 测试 4: 获取未完成任务")
    print("-" * 60)
    
    incomplete = manager.get_incomplete_tasks()
    print(f"  未完成任务数: {len(incomplete)}")
    for task in incomplete:
        print(f"    - {task['task_id']}: {task['status']}")
    
    print()
    
    # 5. 统计信息
    print("📊 测试 5: 任务统计")
    print("-" * 60)
    
    stats = manager.get_statistics()
    print(f"  总任务数: {stats['total']}")
    print(f"  排队中: {stats['queued']}")
    print(f"  处理中: {stats['processing']}")
    print(f"  已完成: {stats['completed']}")
    print(f"  失败: {stats['failed']}")
    
    print()
    
    # 6. 删除任务
    print("🗑️  测试 6: 删除任务")
    print("-" * 60)
    
    success = manager.delete_task("task-queued")
    status_icon = "✅" if success else "❌"
    print(f"  {status_icon} 删除任务: task-queued")
    
    # 验证删除
    remaining = manager.load_all_tasks()
    print(f"  剩余任务数: {len(remaining)}")
    
    print()
    
    # 7. 清理
    print("🧹 测试 7: 清理测试数据")
    print("-" * 60)
    
    if storage_file.exists():
        storage_file.unlink()
        print(f"  ✅ 已删除测试文件: {storage_file}")
    
    print()
    print("=" * 60)
    print("✅ 所有测试完成！")
    print("=" * 60)


def test_recovery_simulation():
    """模拟任务恢复场景"""
    
    storage_file = Path(__file__).parent.parent / "data" / "test_recovery.json"
    manager = TaskPersistenceManager(storage_file)
    
    print("\n" + "=" * 60)
    print("🔄 任务恢复场景模拟")
    print("=" * 60)
    print()
    
    # 场景 1: 模拟 API 关闭前的状态
    print("📝 场景 1: API 关闭前")
    print("-" * 60)
    
    tasks_before_shutdown = {
        "task-running": {
            "task_id": "task-running",
            "status": "processing",
            "prompt_id": "prompt-abc",
            "created_at": datetime.now().isoformat(),
            "params": {"num_frames": 100}
        },
        "task-waiting": {
            "task_id": "task-waiting",
            "status": "queued",
            "created_at": datetime.now().isoformat(),
            "params": {"num_frames": 50}
        }
    }
    
    for task_id, task_data in tasks_before_shutdown.items():
        manager.save_task(task_id, task_data)
        print(f"  💾 保存任务: {task_id} ({task_data['status']})")
    
    print(f"\n  💥 API 关闭...\n")
    
    # 场景 2: 模拟 API 重启
    print("🚀 场景 2: API 重启")
    print("-" * 60)
    
    # 从磁盘加载
    recovered_tasks = manager.load_all_tasks()
    print(f"  📂 从磁盘加载了 {len(recovered_tasks)} 个任务:")
    
    for task_id, task_data in recovered_tasks.items():
        status = task_data['status']
        prompt_id = task_data.get('prompt_id', 'N/A')
        
        print(f"\n  📋 恢复任务: {task_id}")
        print(f"     原状态: {status}")
        
        if status in ['queued', 'processing']:
            if prompt_id != 'N/A':
                print(f"     Prompt ID: {prompt_id}")
                print(f"     🔍 查询 ComfyUI 状态...")
                print(f"     (实际使用时会从 ComfyUI API 获取)")
                
                # 模拟从 ComfyUI 查询到的状态
                simulated_status = "completed"  # 假设已完成
                print(f"     ✅ 新状态: {simulated_status}")
                
                # 更新状态
                task_data['status'] = simulated_status
                manager.save_task(task_id, task_data)
            else:
                print(f"     ⏰ 保持 {status} 状态")
    
    print()
    
    # 清理
    print("🧹 清理测试数据")
    print("-" * 60)
    if storage_file.exists():
        storage_file.unlink()
        print(f"  ✅ 已删除: {storage_file}")
    
    print()


if __name__ == '__main__':
    try:
        # 运行基础功能测试
        test_persistence()
        
        # 运行恢复场景模拟
        test_recovery_simulation()
        
        print("✅ 所有测试通过！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
