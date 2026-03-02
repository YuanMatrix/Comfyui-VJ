# 📦 任务持久化与恢复功能

## 功能概述

当 API 服务关闭时，正在运行的任务信息会**自动保存到磁盘**。重启 API 时，会**自动恢复**这些任务，并尝试从 ComfyUI 获取最新状态。

## 工作原理

### 1. 自动持久化

任务在以下时机会自动保存到磁盘：

✅ **任务创建时** (`queued` 状态)
```python
tasks[task_id] = {
    "task_id": "abc-123",
    "status": "queued",
    ...
}
persist_task(task_id)  # 💾 保存到磁盘
```

✅ **任务开始处理时** (`processing` 状态)
```python
tasks[task_id]['status'] = 'processing'
tasks[task_id]['prompt_id'] = 'prompt-456'
persist_task(task_id)  # 💾 保存 prompt_id
```

✅ **任务完成时** (`completed` 状态)
```python
tasks[task_id]['status'] = 'completed'
tasks[task_id]['output_files'] = [...]
persist_task(task_id)  # 💾 保存结果
```

✅ **任务失败时** (`failed` 状态)
```python
tasks[task_id]['status'] = 'failed'
tasks[task_id]['error'] = "..."
persist_task(task_id)  # 💾 保存错误信息
```

### 2. 存储位置

```
vj/
├── data/
│   └── tasks.json  ← 所有任务数据
├── video_generation_api.py
└── task_persistence.py
```

### 3. 启动时恢复

```
┌─────────────────────────┐
│  启动 API 服务          │
└───────────┬─────────────┘
            │
            ↓
┌─────────────────────────┐
│  加载 tasks.json        │
│  恢复所有任务到内存     │
└───────────┬─────────────┘
            │
            ↓
    ┌───────┴────────┐
    │                │
    ↓                ↓
┌───────────┐  ┌──────────────┐
│ 已完成    │  │ 未完成       │
│ completed │  │ queued       │
│ failed    │  │ processing   │
└───────────┘  └──────┬───────┘
                      │
                      ↓
              ┌───────────────┐
              │ 查询 ComfyUI  │
              │ 获取最新状态  │
              └───────┬───────┘
                      │
          ┌───────────┼───────────┐
          │           │           │
          ↓           ↓           ↓
      ┌────────┐  ┌────────┐  ┌────────┐
      │已完成  │  │失败    │  │处理中  │
      │更新状态│  │更新状态│  │保持    │
      └────────┘  └────────┘  └────────┘
```

## 使用场景

### 场景 1: 正常关闭后重启

```bash
# 1. API 正在运行，有 3 个任务
Task A: completed  ✅
Task B: processing ⏳
Task C: queued     ⏰

# 2. 关闭 API (Ctrl+C)
# 所有任务自动保存到 tasks.json

# 3. 重启 API
bash vj/start_vj_api.sh

# 4. 自动恢复
🔄 正在恢复之前的任务...
============================================================
📋 恢复任务: task-B
   原状态: processing
   Prompt ID: prompt-456
   新状态: completed  ✅ (从 ComfyUI 查询到已完成)

📋 恢复任务: task-C
   原状态: queued
   新状态: queued  ⏰ (保持原状态)

📊 任务恢复完成:
   总任务数: 3
   已恢复: 3
   新完成: 1
   新失败: 0
============================================================
```

### 场景 2: 意外崩溃后重启

```bash
# 1. API 崩溃前的状态
Task X: processing (prompt_id: prompt-789)

# 2. API 崩溃 💥

# 3. 重启 API
bash vj/start_vj_api.sh

# 4. 自动恢复并查询 ComfyUI
🔄 正在恢复之前的任务...
📋 恢复任务: task-X
   原状态: processing
   Prompt ID: prompt-789
   
   查询 ComfyUI...
   
   ✅ 新状态: completed
   📹 输出文件: /Users/.../output/vj/video.mp4
```

### 场景 3: 长时间关闭后重启

```bash
# 1. API 关闭时有未完成任务
Task M: processing (运行了 50%)

# 2. 关闭 API 一天

# 3. 重启 API
bash vj/start_vj_api.sh

# 4. 查询 ComfyUI 状态
📋 恢复任务: task-M
   原状态: processing
   Prompt ID: prompt-999
   
   查询 ComfyUI...
   
   两种可能:
   ✅ 完成了: 更新为 completed，恢复输出文件
   ❌ 失败了: 更新为 failed，记录错误信息
   ⚠️  无记录: 保持 processing (需要手动检查)
```

## API 端点

### 查询恢复的任务

```bash
# 列出所有任务（包括恢复的）
curl http://localhost:5002/api/tasks

# 查询特定任务
curl http://localhost:5002/api/tasks/abc-123

# 筛选处理中的任务
curl "http://localhost:5002/api/tasks?status=processing"
```

### 清理旧任务

```python
# 可以在 Python 中调用
from vj.task_persistence import TaskPersistenceManager

manager = TaskPersistenceManager("vj/data/tasks.json")

# 清理 7 天前的任务
cleaned = manager.cleanup_old_tasks(days=7)
print(f"清理了 {cleaned} 个旧任务")
```

## 任务数据结构

### tasks.json 格式

```json
{
  "abc-123": {
    "task_id": "abc-123",
    "status": "completed",
    "params": {
      "audio_path": "/Users/.../input/task/audio.mp3",
      "num_frames": 100,
      "width": 512,
      "height": 512,
      "fps": 16,
      "images": ["task/img1.jpg", "task/img2.jpg"]
    },
    "created_at": "2026-02-07T10:00:00",
    "completed_at": "2026-02-07T10:05:00",
    "client_id": "client-456",
    "prompt_id": "prompt-789",
    "output_files": [
      {
        "filename": "video_00001.mp4",
        "subfolder": "vj",
        "type": "output",
        "path": "/Users/.../output/vj/video_00001.mp4"
      }
    ],
    "error": null,
    "elapsed_seconds": 300
  }
}
```

## 状态恢复规则

| 原状态 | Prompt ID | ComfyUI 状态 | 恢复后状态 | 说明 |
|--------|-----------|--------------|------------|------|
| `queued` | ❌ 无 | - | `queued` | 保持原状态 |
| `processing` | ✅ 有 | completed | `completed` | 任务已完成 ✅ |
| `processing` | ✅ 有 | failed | `failed` | 任务失败 ❌ |
| `processing` | ✅ 有 | 无记录 | `processing` | 保持，需人工检查 ⚠️ |
| `completed` | - | - | `completed` | 直接恢复 |
| `failed` | - | - | `failed` | 直接恢复 |

## 注意事项

### 1. ⚠️ 任务不会自动重新执行

恢复的任务**只更新状态**，不会重新执行。如果任务在 `queued` 状态关闭，重启后仍然是 `queued`，需要手动触发。

**解决方案**: 如果需要重新执行，删除任务后重新提交：

```bash
# 删除未完成的任务
curl -X DELETE http://localhost:5002/api/tasks/abc-123

# 重新提交
curl -X POST http://localhost:5002/api/generate-video \
     -H "Content-Type: application/json" \
     -d '{"audio_path": "...", ...}'
```

### 2. ⚠️ 依赖 ComfyUI 的历史记录

恢复 `processing` 状态的任务需要查询 ComfyUI 的 `/history/{prompt_id}` 端点。如果 ComfyUI 也重启了，历史记录可能丢失。

**建议**: 
- 在生产环境中配置 ComfyUI 的历史记录持久化
- 或在重启前确保所有任务已完成

### 3. ⚠️ 文件路径有效性

恢复的任务中的文件路径（input/output）必须仍然有效。如果文件被移动或删除，任务虽然恢复，但文件可能不可用。

### 4. ✅ 向后兼容

如果 `tasks.json` 不存在或为空，API 会正常启动，不影响新任务的创建。

## 测试恢复功能

### 测试脚本

```bash
# 1. 启动 API
bash vj/start_vj_api.sh

# 2. 提交一个任务
curl -X POST http://localhost:5002/api/generate-video \
     -H "Content-Type: application/json" \
     -d '{
       "audio_path": "test/audio.mp3",
       "images": ["test/img1.jpg", ...],
       "num_frames": 50,
       "width": 384,
       "height": 384,
       "fps": 16
     }'

# 记录返回的 task_id
TASK_ID="abc-123"

# 3. 等待任务开始处理（status 变为 processing）
sleep 5

# 4. 关闭 API (Ctrl+C)

# 5. 检查 tasks.json
cat vj/data/tasks.json

# 6. 重启 API
bash vj/start_vj_api.sh

# 观察恢复过程的日志输出

# 7. 查询任务状态
curl http://localhost:5002/api/tasks/$TASK_ID
```

## 最佳实践

### 1. 定期清理旧任务

```bash
# 添加到 crontab，每天清理 7 天前的任务
0 0 * * * cd /path/to/ComfyUI && python3 << EOF
from vj.task_persistence import TaskPersistenceManager
from pathlib import Path
manager = TaskPersistenceManager(Path("vj/data/tasks.json"))
cleaned = manager.cleanup_old_tasks(days=7)
print(f"清理了 {cleaned} 个任务")
EOF
```

### 2. 备份任务数据

```bash
# 定期备份 tasks.json
cp vj/data/tasks.json vj/data/tasks.json.backup
```

### 3. 监控未完成任务

```python
# 检查是否有长时间未完成的任务
from vj.task_persistence import TaskPersistenceManager
from datetime import datetime, timedelta

manager = TaskPersistenceManager("vj/data/tasks.json")
incomplete = manager.get_incomplete_tasks()

for task in incomplete:
    created = datetime.fromisoformat(task['created_at'])
    age = datetime.now() - created
    
    if age > timedelta(hours=1):
        print(f"⚠️  任务 {task['task_id']} 已运行 {age.seconds/3600:.1f} 小时")
```

## 总结

✅ **自动保存**: 任务状态变化时自动保存  
✅ **自动恢复**: 启动时自动加载并更新状态  
✅ **智能查询**: 从 ComfyUI 获取最新状态  
✅ **持久存储**: JSON 文件，易于查看和调试  
✅ **向后兼容**: 不影响现有功能  

现在你可以放心地关闭和重启 API，任务信息不会丢失！🎉
