# 🎬 VJ 视频生成 API 服务

基于 ComfyUI 的音频反应式视频生成 API 服务。通过简单的 RESTful API 调用，自动生成炫酷的音频反应式视频。

## 📋 功能特性

- ✅ **简单易用**：RESTful API，支持 JSON 请求
- ✅ **参数可控**：自定义帧数、分辨率、帧率、图片
- ✅ **异步处理**：任务队列，支持并发处理
- ✅ **实时进度**：随时查询任务状态和进度
- ✅ **视频下载**：生成完成后直接下载
- ✅ **任务管理**：列出、查询、取消任务

## 🚀 快速开始

### 1. 前置条件

确保 ComfyUI 已经在运行：

```bash
cd /Users/coco/coco-code/ComfyUI
python main.py
```

### 2. 启动 API 服务

```bash
cd /Users/coco/coco-code/ComfyUI
./vj/start_vj_api.sh
```

服务将在 `http://localhost:5002` 启动。

### 3. 测试 API

运行测试脚本：

```bash
python3 vj/test_vj_api.py
```

## 📖 API 文档

### 基础信息

- **Base URL**: `http://localhost:5002`
- **数据格式**: JSON
- **认证**: 无（本地服务）

### 端点列表

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/` | 服务信息 |
| GET | `/health` | 健康检查 |
| **POST** | **`/api/upload-image`** | **上传图片** |
| **POST** | **`/api/upload-audio`** | **上传音频** |
| POST | `/api/generate-video` | 生成视频 |
| GET | `/api/tasks/{task_id}` | 查询任务状态 |
| GET | `/api/tasks` | 列出所有任务 |
| GET | `/api/tasks/{task_id}/download` | 下载视频 |
| DELETE | `/api/tasks/{task_id}` | 取消任务 |

---

### 1. 上传图片 🆕

**请求方式1 - multipart/form-data（推荐）**

```http
POST /api/upload-image
Content-Type: multipart/form-data

file: <图片文件>
filename: "my_image.jpg"  // 可选，自定义文件名
```

**请求方式2 - JSON Base64**

```http
POST /api/upload-image
Content-Type: application/json

{
  "filename": "my_image.jpg",
  "data": "base64_encoded_image_data"
}
```

**响应**

```json
{
  "success": true,
  "filename": "my_image.jpg",
  "path": "/Users/coco/coco-code/ComfyUI/input/my_image.jpg",
  "size": 1024000,
  "message": "图片上传成功"
}
```

**支持的图片格式**
- `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.webp`

---

### 2. 上传音频 🆕

**请求方式1 - multipart/form-data（推荐）**

```http
POST /api/upload-audio
Content-Type: multipart/form-data

file: <音频文件>
filename: "my_audio.mp3"  // 可选
```

**请求方式2 - JSON Base64**

```http
POST /api/upload-audio
Content-Type: application/json

{
  "filename": "my_audio.mp3",
  "data": "base64_encoded_audio_data"
}
```

**响应**

```json
{
  "success": true,
  "filename": "my_audio.mp3",
  "path": "/Users/coco/coco-code/ComfyUI/input/my_audio.mp3",
  "size": 2048000,
  "message": "音频上传成功"
}
```

**支持的音频格式**
- `.mp3`, `.wav`, `.ogg`, `.flac`, `.m4a`, `.aac`

---

### 3. 生成视频

**请求**

```http
POST /api/generate-video
Content-Type: application/json

{
  "audio_path": "demo3.mp3",
  "num_frames": 50,
  "width": 384,
  "height": 384,
  "fps": 16,
  "images": ["11.jpg", "12.jpg", "13.jpg", "14.jpg"]
}
```

**参数说明**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `audio_path` | string | ✅ | - | 音频文件路径（相对于 `input/` 或绝对路径） |
| `num_frames` | integer | ❌ | 50 | 视频总帧数（1-500） |
| `width` | integer | ❌ | 384 | 视频宽度（256/384/512/768/1024） |
| `height` | integer | ❌ | 384 | 视频高度（256/384/512/768/1024） |
| `fps` | float | ❌ | 16 | 帧率（8-60） |
| `images` | array | ❌ | `["11.jpg", ...]` | 图片文件名列表（相对于 `input/`） |

**响应**

```json
{
  "success": true,
  "task_id": "abc-123-def-456",
  "status": "queued",
  "message": "任务已提交，正在处理中",
  "check_status_url": "/api/tasks/abc-123-def-456"
}
```

**HTTP 状态码**
- `202 Accepted`: 任务已提交
- `400 Bad Request`: 参数错误
- `500 Internal Server Error`: 服务器错误

---

### 4. 查询任务状态

**请求**

```http
GET /api/tasks/{task_id}
```

**响应**

```json
{
  "success": true,
  "task": {
    "task_id": "abc-123-def-456",
    "status": "processing",
    "params": {
      "audio_path": "/path/to/audio.mp3",
      "num_frames": 50,
      "width": 384,
      "height": 384,
      "fps": 16,
      "images": ["11.jpg", "12.jpg", "13.jpg", "14.jpg"]
    },
    "created_at": "2026-02-04T10:00:00",
    "prompt_id": "xyz-789",
    "elapsed_seconds": 120,
    "output_files": [],
    "error": null
  }
}
```

**当任务完成时的响应（新增 `video_path` 字段）**

```json
{
  "success": true,
  "task": {
    "task_id": "abc-123-def-456",
    "status": "completed",
    "params": {...},
    "created_at": "2026-02-04T10:00:00",
    "completed_at": "2026-02-04T10:05:30",
    "elapsed_seconds": 330,
    "output_files": [
      {
        "filename": "02-07_00001-audio.mp4",
        "subfolder": "AudioReactive_Yvann/ImagesToVideo/FirstPass",
        "type": "output",
        "path": "/Users/coco/coco-code/ComfyUI/output/AudioReactive_Yvann/ImagesToVideo/FirstPass/02-07_00001-audio.mp4"
      }
    ],
    "video_path": "/Users/coco/coco-code/ComfyUI/output/AudioReactive_Yvann/ImagesToVideo/FirstPass/02-07_00001-audio.mp4",
    "error": null
  }
}
```

**重要字段说明**

| 字段 | 类型 | 说明 |
|------|------|------|
| `video_path` | string | **仅在 `status='completed'` 时返回**，视频文件的绝对路径，可直接读取 |
| `video_paths` | array | 如果生成了多个视频文件，包含所有视频的绝对路径列表 |
| `output_files` | array | 详细的输出文件信息（包含文件名、子目录等） |

**任务状态**

| 状态 | 说明 |
|------|------|
| `queued` | 已提交，等待处理 |
| `processing` | 正在处理中 |
| `completed` | 已完成 |
| `failed` | 失败 |
| `cancelled` | 已取消 |

---

### 5. 列出所有任务

**请求**

```http
GET /api/tasks?limit=10&status=completed
```

**参数**
- `limit` (integer): 返回数量限制，默认 50
- `status` (string): 筛选状态（queued/processing/completed/failed）

**响应**

```json
{
  "success": true,
  "tasks": [
    {
      "task_id": "abc-123",
      "status": "completed",
      "created_at": "2026-02-04T10:00:00",
      "params": {...}
    }
  ],
  "total": 1
}
```

---

### 6. 下载视频

**请求**

```http
GET /api/tasks/{task_id}/download?index=0
```

**参数**
- `index` (integer): 文件索引，默认 0（第一个文件）

**响应**
- 成功：返回视频文件（`video/mp4`）
- 失败：返回 JSON 错误信息

---

### 7. 取消任务

**请求**

```http
DELETE /api/tasks/{task_id}
```

**响应**

```json
{
  "success": true,
  "message": "任务已取消"
}
```

---

### 8. 健康检查

**请求**

```http
GET /health
```

**响应**

```json
{
  "status": "healthy",
  "comfyui": "running",
  "tasks_count": 5
}
```

## 💡 使用示例

### 示例 1: 上传文件并生成视频 🆕

```python
import requests
import time

# 1. 上传图片
image_files = ['image1.jpg', 'image2.jpg', 'image3.jpg', 'image4.jpg']
uploaded_images = []

for img_file in image_files:
    with open(img_file, 'rb') as f:
        files = {'file': f}
        response = requests.post('http://localhost:5002/api/upload-image', files=files)
    
    if response.status_code == 201:
        result = response.json()
        uploaded_images.append(result['filename'])
        print(f"✅ 上传成功: {result['filename']}")

# 2. 上传音频
with open('my_audio.mp3', 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:5002/api/upload-audio', files=files)

uploaded_audio = response.json()['filename']
print(f"✅ 音频上传成功: {uploaded_audio}")

# 3. 使用上传的文件生成视频
response = requests.post('http://localhost:5002/api/generate-video', json={
    "audio_path": uploaded_audio,     # 使用上传的音频
    "images": uploaded_images,         # 使用上传的图片
    "num_frames": 50,
    "width": 384,
    "height": 384,
    "fps": 16
})

task_id = response.json()['task_id']
print(f"任务ID: {task_id}")

# 4. 等待完成
while True:
    response = requests.get(f'http://localhost:5002/api/tasks/{task_id}')
    task = response.json()['task']
    
    if task['status'] == 'completed':
        video_path = task['video_path']
        print(f"✅ 完成！视频路径: {video_path}")
        break
    
    time.sleep(3)
```

### 示例 2: 直接使用现有文件

```python
import requests
import time

# 1. 提交视频生成任务
response = requests.post('http://localhost:5002/api/generate-video', json={
    "audio_path": "demo3.mp3",
    "num_frames": 50,
    "width": 384,
    "height": 384,
    "fps": 16,
    "images": ["11.jpg", "12.jpg", "13.jpg", "14.jpg"]
})

task_id = response.json()['task_id']
print(f"任务ID: {task_id}")

# 2. 轮询任务状态
while True:
    response = requests.get(f'http://localhost:5002/api/tasks/{task_id}')
    task = response.json()['task']
    
    print(f"状态: {task['status']}, 已耗时: {task['elapsed_seconds']}秒")
    
    if task['status'] in ['completed', 'failed']:
        break
    
    time.sleep(3)

# 3. 获取视频路径并使用（推荐方式）
if task['status'] == 'completed':
    video_path = task['video_path']  # 获取绝对路径
    print(f"✅ 视频生成成功！")
    print(f"📹 视频路径: {video_path}")
    
    # 方式1: 直接读取文件
    with open(video_path, 'rb') as f:
        video_data = f.read()
    
    # 方式2: 或者通过 API 下载
    response = requests.get(f'http://localhost:5002/api/tasks/{task_id}/download')
    with open('output.mp4', 'wb') as f:
        f.write(response.content)
    print("视频已下载！")
```

### cURL 示例

```bash
# 生成视频
curl -X POST http://localhost:5002/api/generate-video \
  -H "Content-Type: application/json" \
  -d '{
    "audio_path": "demo3.mp3",
    "num_frames": 50,
    "width": 384,
    "height": 384,
    "fps": 16
  }'

# 查询状态
curl http://localhost:5002/api/tasks/abc-123-def

# 下载视频
curl http://localhost:5002/api/tasks/abc-123-def/download -o output.mp4
```

### JavaScript 示例

```javascript
// 使用 fetch API
async function generateVideo() {
  // 提交任务
  const response = await fetch('http://localhost:5002/api/generate-video', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      audio_path: 'demo3.mp3',
      num_frames: 50,
      width: 384,
      height: 384,
      fps: 16,
      images: ['11.jpg', '12.jpg', '13.jpg', '14.jpg']
    })
  });
  
  const result = await response.json();
  const taskId = result.task_id;
  console.log('任务ID:', taskId);
  
  // 轮询状态
  while (true) {
    const statusResponse = await fetch(`http://localhost:5002/api/tasks/${taskId}`);
    const statusResult = await statusResponse.json();
    const task = statusResult.task;
    
    console.log(`状态: ${task.status}, 已耗时: ${task.elapsed_seconds}秒`);
    
    if (task.status === 'completed' || task.status === 'failed') {
      break;
    }
    
    await new Promise(resolve => setTimeout(resolve, 3000));
  }
  
  // 下载视频
  window.location.href = `http://localhost:5002/api/tasks/${taskId}/download`;
}

generateVideo();
```

## 🔧 技术架构

### 核心技术栈

- **Flask**: Web 框架
- **ComfyUI**: 图像生成引擎
- **Threading**: 异步任务处理
- **Requests**: HTTP 客户端

### 工作流程

```
1. 客户端提交请求
   ↓
2. API 验证参数
   ↓
3. 加载 workflow 模板
   ↓
4. 更新参数（音频、帧数、图片等）
   ↓
5. 提交到 ComfyUI
   ↓
6. 异步等待执行完成
   ↓
7. 返回结果给客户端
```

### 目录结构

```
ComfyUI/
├── vj/
│   ├── video_generation_api.py  # API 服务主程序
│   ├── start_vj_api.sh          # 启动脚本
│   ├── test_vj_api.py           # 测试脚本
│   └── README.md                # 本文档
├── user/default/workflows/
│   └── coco_full.json           # Workflow 模板
├── input/                       # 输入文件目录
│   ├── demo3.mp3
│   ├── 11.jpg
│   └── ...
└── output/                      # 输出文件目录
```

## ⚙️ 配置说明

### 修改端口

编辑 `video_generation_api.py`：

```python
# 修改最后一行
app.run(host='0.0.0.0', port=5002, debug=True, threaded=True)
#                             ^^^^
#                             改成你想要的端口
```

### 修改 ComfyUI 地址

如果 ComfyUI 运行在其他地址：

```python
# 修改配置部分
COMFYUI_URL = "http://127.0.0.1:8188"  # 改成实际地址
```

### 修改 Workflow 模板

如果使用其他 workflow：

```python
WORKFLOW_TEMPLATE = BASE_DIR / "user/default/workflows/your_workflow.json"
```

## 🐛 故障排除

### 问题 1: ComfyUI 未运行

**错误信息**:
```
⚠️  警告: ComfyUI 未运行
```

**解决方法**:
```bash
# 先启动 ComfyUI
cd /Users/coco/coco-code/ComfyUI
python main.py
```

---

### 问题 2: 任务一直处于 queued 状态

**可能原因**:
- ComfyUI 没有响应
- workflow 有错误

**解决方法**:
1. 检查 ComfyUI 日志
2. 手动在 ComfyUI UI 中测试 workflow
3. 检查 API 服务日志

---

### 问题 3: 音频或图片文件找不到

**错误信息**:
```json
{
  "success": false,
  "error": "音频文件不存在: demo3.mp3"
}
```

**解决方法**:
1. 检查文件是否在 `input/` 目录
2. 使用绝对路径
3. 检查文件名拼写

---

### 问题 4: 生成的视频不符合预期

**可能原因**:
- workflow 模板问题
- 参数设置不合理

**解决方法**:
1. 在 ComfyUI UI 中测试并调整 workflow
2. 保存为新模板
3. 修改 API 配置使用新模板

## 📊 性能优化

### 并发处理

当前版本支持多线程并发处理多个任务，但受限于 ComfyUI 本身的处理能力。

### 任务队列

生产环境建议使用 Celery + Redis 替代内存任务队列：

```python
# 安装 Celery
pip install celery redis

# 配置 Celery
from celery import Celery
app = Celery('vj_api', broker='redis://localhost:6379/0')
```

### 存储优化

当前任务信息存储在内存中，重启服务后丢失。生产环境建议使用数据库（SQLite、PostgreSQL）。

## 🔐 安全建议

### 生产环境部署

1. **添加认证**：使用 JWT 或 API Key
2. **限流**：防止 API 滥用（Flask-Limiter）
3. **HTTPS**：使用 SSL 证书
4. **防火墙**：限制访问 IP
5. **文件验证**：检查上传文件类型和大小

### 示例：添加 API Key 认证

```python
from functools import wraps

API_KEY = "your-secret-api-key"

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if api_key != API_KEY:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/api/generate-video', methods=['POST'])
@require_api_key
def generate_video():
    # ...
```

## 📝 开发指南

### 添加新功能

1. 修改 `video_generation_api.py`
2. 添加新的端点
3. 更新 `README.md`
4. 添加测试用例到 `test_vj_api.py`

### 调试模式

API 默认启用 Flask 调试模式，自动重载代码：

```python
app.run(debug=True)  # 已启用
```

### 日志记录

添加日志输出：

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("任务已提交")
logger.error(f"任务失败: {error}")
```

## 📄 许可证

本项目基于 ComfyUI，遵循相关开源协议。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📞 支持

如有问题，请联系项目维护者或提交 Issue。

---

**Happy Coding! 🎉**
