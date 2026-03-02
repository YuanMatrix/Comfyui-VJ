# 🎬 VJ 视频生成 API 服务

基于 ComfyUI 的音频反应式视频生成 API 服务。通过简单的 RESTful API 调用，自动生成炫酷的音频反应式视频。

## 📚 文档总索引（总览 → 对应文件）

### 这份文档（`ComfyUI/vj/README.md`）
- 整体架构、接口说明、参数示例、启动方式、任务机制、故障排查、性能与安全建议。

### 相关服务文档（建议按职责阅读）
- `ComfyUI/vj/VJ_API运行成功.md`：VJ API 启动成功后的运行摘要与快速验证命令。
- `ComfyUI/vj/VJ_API日志说明.md`：日志分类、排障方法、如何确认接口被调用。
- `ComfyUI/vj/config.json`：服务配置中心（ComfyUI 地址、workflow 模板、输入输出目录、参数上限、超时）。
- `ComfyUI/vj/requirements.txt`：`@ComfyUI/vj` 运行依赖。
- `ComfyUI/vj/start_vj_api.sh`、`ComfyUI/vj/start_vj_api.bat`：VJ API 启动脚本。
- `ComfyUI/vj/task_persistence.py`：任务落盘与重启恢复逻辑。

### 前端文档（`@vj-disp-fe`）
- `vj-disp-fe/README.txt`：前端工程快速启动说明。
- `vj-disp-fe/Windows使用说明.md`：Windows 启动与常见问题。
- `vj-disp-fe/ComfyUI配置说明.md`：`COMFYUI_OUTPUT_BASE` 与输出代理说明。
- `vj-disp-fe/app/api/comfyui/*/route.ts`：前端代理接口源码（upload/generate/status/output）。

### 业务关系
- `ComfyUI` 作为算法端（端口 8188）负责实际渲染；
- `@ComfyUI/vj` 作为任务编排服务（端口 5002）负责参数验收和 workflow 注入；
- `@vj-disp-fe` 作为体验层（端口 3000）负责上传、发起生成、轮询与播放。

## 🧩 整体模块图（前端 → 服务端 → 算法端）

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                       @vj-disp-fe  前端  :3000                               │
│                                                                              │
│   浏览器页面                                                                  │
│   ├── 上传音乐/图片 ──→ Next.js API 代理: POST /api/comfyui/upload            │
│   │                      body: { file, taskId, fileType: "audio"|"image" }  │
│   │                                                                          │
│   ├── 生成视频     ──→ Next.js API 代理: POST /api/comfyui/generate           │
│   │                      body: { audioPath, images[], numFrames,             │
│   │                              width, height, fps }                        │
│   │                                                                          │
│   ├── 轮询状态     ──→ Next.js API 代理: GET  /api/comfyui/status/{taskId}    │
│   │                      → 返回: { status, videoPath, elapsedSeconds }       │
│   │                                                                          │
│   └── 播放视频     ──→ Next.js API 代理: GET  /api/comfyui/output/[...path]   │
│                         → 读取磁盘文件流返回浏览器                            │
│                         (配置: COMFYUI_OUTPUT_BASE 指定本地 output 根路径)   │
└─────────────────────────────────┬────────────────────────────────────────────┘
                                  │  HTTP  (COMFYUI_API_BASE=http://localhost:5002/api)
                                  ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    @ComfyUI/vj  任务服务  :5002                               │
│                    video_generation_api.py (Flask)                           │
│                                                                              │
│  ┌─ 文件上传 ──────────────────────────────────────────────────────────────┐ │
│  │  POST /api/upload-audio                                                 │ │
│  │       body: file(multipart) | { filename, data(base64) }               │ │
│  │       → 保存到 input/{task_id}/filename                                 │ │
│  │  POST /api/upload-image    (同上，支持 jpg/png/webp/gif/bmp)            │ │
│  └──────────────────────────────────────────────────────────────────────── ┘ │
│                                                                              │
│  ┌─ 视频生成 ──────────────────────────────────────────────────────────────┐ │
│  │  POST /api/generate-video                                               │ │
│  │       body: {                                                           │ │
│  │         audio_path: string   ← 必填，相对 input/ 或绝对路径             │ │
│  │         images: string[]     ← 必填，4~10 张，相对 input/               │ │
│  │         num_frames: int      ← 默认 480，范围 [10~5000]  ← config.json  │ │
│  │         width: int           ← 默认 480，范围 [64~2048]  ← config.json  │ │
│  │         height: int          ← 默认 300，范围 [64~2048]  ← config.json  │ │
│  │         fps: float           ← 默认 16，范围 [8~30]      ← config.json  │ │
│  │       }                                                                 │ │
│  │    1. 加载 workflow JSON (config: paths.workflow_template)              │ │
│  │    2. 清洗注释节点 / 修正 KSampler/LoRA 错误参数                        │ │
│  │    3. 按参数重写节点:                                                   │ │
│  │         LoadAudio ← audio_path                                          │ │
│  │         LoadImage × N ← images[]                                        │ │
│  │         INTConstant "Number of Frames" ← num_frames                    │ │
│  │         INTConstant "Width/Height Animation" ← width, height            │ │
│  │         FloatConstant "Frames per second" ← fps                         │ │
│  │         VHS_VideoCombine.filename_prefix ← "vj/{task_id}_"             │ │
│  │    4. 提交到 ComfyUI → 返回 task_id                                     │ │
│  └──────────────────────────────────────────────────────────────────────── ┘ │
│                                                                              │
│  ┌─ 任务管理 ──────────────────────────────────────────────────────────────┐ │
│  │  GET    /api/tasks/{task_id}          → 查状态 / video_path            │ │
│  │  GET    /api/tasks?limit&status       → 任务列表                        │ │
│  │  GET    /api/tasks/{task_id}/download → 直接下载 mp4                    │ │
│  │  DELETE /api/tasks/{task_id}          → 取消 + 通知 ComfyUI /interrupt  │ │
│  │  GET    /health                       → { status, comfyui, task_count } │ │
│  │                                                                         │ │
│  │  任务状态: queued → processing → completed / failed / cancelled         │ │
│  │  持久化:  data/tasks.json   (重启时自动恢复 queued/processing 任务)     │ │
│  └──────────────────────────────────────────────────────────────────────── ┘ │
│                                                                              │
│  ┌─ 配置文件 config.json ──────────────────────────────────────────────────┐ │
│  │  comfyui.url            = http://127.0.0.1:8188   ← ComfyUI 地址       │ │
│  │  comfyui.ws_url         = ws://127.0.0.1:8188/ws                       │ │
│  │  api.port               = 5002                    ← 服务端口            │ │
│  │  paths.workflow_template= user/default/workflows/i2v-final.json        │ │
│  │  paths.input_dir        = input                                         │ │
│  │  paths.output_dir       = output                                        │ │
│  │  limits.*               = 参数合法性边界                                │ │
│  │  timeout.task_execution = 6000  (秒)                                   │ │
│  └──────────────────────────────────────────────────────────────────────── ┘ │
└─────────────────────────────────┬────────────────────────────────────────────┘
                                  │  HTTP  (固定: http://127.0.0.1:8188)
                                  ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                       ComfyUI  算法端  :8188                                 │
│                       python main.py                                         │
│                                                                              │
│   POST /prompt                                                               │
│        body: { client_id, prompt: { <workflow_api_json> } }                 │
│        → 返回: { prompt_id }                                                 │
│                                                                              │
│   GET  /history/{prompt_id}                                                  │
│        → 轮询: { status: {status_str, completed}, outputs: {node_id:...} }  │
│        → 完成后 outputs["410"].gifs[] 包含视频文件名/子目录                  │
│                                                                              │
│   GET  /system_stats   → 健康检查                                            │
│   POST /interrupt      → 中止当前任务                                        │
│   WebSocket :8188/ws   → 实时状态推送（可选）                                │
│                                                                              │
│   Workflow JSON (i2v-final.json) 节点说明:                                   │
│   ├── LoadAudio         → 音频输入                                           │
│   ├── LoadImage × N    → 图片输入（4-10 张，动态节点）                       │
│   ├── ImageBatchMulti  → 批量图片合并（节点 376）                            │
│   ├── INTConstant      → 帧数 / 宽度 / 高度                                 │
│   ├── FloatConstant    → FPS                                                 │
│   ├── KSampler         → 采样器                                              │
│   └── VHS_VideoCombine → 输出视频（节点 410，输出到 output/vj/）            │
│                                                                              │
│   文件系统:                                                                  │
│   input/{task_id}/     ← 上传的音频/图片                                    │
│   output/vj/           ← 生成的视频（{task_id}__00001-audio.mp4）          │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 关键 API 参数清单（可配置项）

#### `@ComfyUI/vj` 接口参数
- `POST /api/upload-image`
  - `file`: 图片文件（建议 JPEG/PNG/WebP）
  - `task_id`: 可选任务目录隔离标识
  - `filename`: 可选重命名
- `POST /api/upload-audio`
  - `file` / `data`
  - `task_id`
  - `filename`
- `POST /api/generate-video`
  - `audio_path`（必填，支持绝对路径或 `input/` 相对路径）
  - `images`（必填，4-10 张）
  - `num_frames`（默认 50，范围受 `config.json` 限制）
  - `width` / `height`（默认 384，受 `config.json` 限制）
  - `fps`（默认 16，受 `config.json` 限制）

#### `@vj-disp-fe` 代理接口参数
- `POST /api/comfyui/upload`
  - `taskId`、`fileType`、`file`
- `POST /api/comfyui/generate`
  - `audioPath`、`images`、`numFrames`、`width`、`height`、`fps`
- `GET /api/comfyui/status/{taskId}`
- `GET /api/comfyui/output/[...path]`（将磁盘文件转 HTTP）

#### ComfyUI 关键内部接口（上游）
- `POST /prompt`：提交 workflow（payload 含 `client_id` 与 `prompt`）
- `GET /history/{prompt_id}`：轮询状态与输出
- `GET /system_stats`：健康检查
- `POST /interrupt`：任务中止

### 可配置点清单
- `ComfyUI/vj/config.json`
  - `comfyui.url` / `comfyui.ws_url`
  - `api.host` / `api.port` / `api.debug`
  - `paths.workflow_template`、`paths.input_dir`、`paths.output_dir`
  - `limits.num_frames_*`、`limits.width_*`、`limits.height_*`、`limits.fps_*`、`limits.max_images`
  - `timeout.task_execution`
- `ComfyUI/vj/start_vj_api.sh` / `start_vj_api.bat`
  - 启动时是否检查依赖、ComfyUI 连通性、工作目录
- `vj-disp-fe/.env.local`
  - `COMFYUI_API_BASE`（默认 `http://localhost:5002/api`）
  - `COMFYUI_OUTPUT_BASE`（用于 output 文件映射根路径）
- `vj-disp-fe/package.json` + 启动脚本
  - `dev` / `build` / `start` 命令与端口策略

---

## 🛠️ 从零开始：完整部署流程

> 按顺序执行，每一步完成后再进行下一步。

---

### 第一步：安装并启动 ComfyUI

#### 1.1 下载 ComfyUI

**方式 A — Windows 便携版（推荐 Windows 用户）**

```
1. 下载: https://github.com/comfyanonymous/ComfyUI/releases/latest/download/ComfyUI_windows_portable_nvidia.7z
2. 用 7-Zip 解压到本地目录，例如: D:\ComfyUI_windows_portable\ComfyUI
3. 使用目录内的 python_embeded\python.exe 运行（不需要另装 Python）
```

**方式 B — macOS / Linux 手动安装**

```bash
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
pip install torch torchvision torchaudio   # NVIDIA: 加 --extra-index-url https://download.pytorch.org/whl/cu130
pip install -r requirements.txt
```

#### 1.2 安装必要的自定义节点

`i2v-final.json` workflow 依赖以下自定义节点，需要通过 **ComfyUI-Manager** 安装：

| 节点名 | 用途 |
|--------|------|
| `comfyui-videohelpersuite` (VHS) | `VHS_VideoCombine` — 视频合并输出 |
| `ComfyUI-AnimateDiff-Evolved` | AnimateDiff 动画帧相关节点 |
| `ComfyUI-Audio` | `LoadAudio` — 音频输入节点 |
| `ComfyUI_IPAdapter_plus` | IP-Adapter 图像风格控制 |

安装 ComfyUI-Manager：

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Comfy-Org/ComfyUI-Manager.git
```

重启 ComfyUI 后，在浏览器 UI 右上角点击 **Manager** → **Install Missing Custom Nodes**，自动检测并安装缺失节点。

#### 1.3 准备模型文件

以下是 `i2v-final.json` workflow 实际使用的所有模型，按目录分类放置：

```
ComfyUI/models/
│
├── checkpoints/
│   └── DreamShaper_8_pruned.safetensors
│       ← 节点: CheckpointLoaderSimple（主文生图模型）
│       ← 下载: https://civitai.com/models/4384/dreamshaper
│
├── vae/
│   └── vae-ft-mse-840000-ema-pruned.safetensors
│       ← 节点: VAELoader
│       ← 下载: https://huggingface.co/stabilityai/sd-vae-ft-mse-original
│
├── loras/
│   ├── AnimateLCM_sd15_t2v_lora.safetensors
│   │   ← 节点: LoraLoaderModelOnly（动画 LCM 加速 LoRA）
│   │   ← 下载: https://huggingface.co/wangfuyun/AnimateLCM
│   └── v3_sd15_adapter.ckpt
│       ← 节点: LoraLoaderModelOnly（SparseCtrl Adapter）
│       ← 下载: https://huggingface.co/guoyww/animatediff
│
├── animatediff_models/
│   └── AnimateLCM_sd15_t2v.ckpt
│       ← 节点: ADE_LoadAnimateDiffModel（AnimateDiff 运动主模型）
│       ← 下载: https://huggingface.co/wangfuyun/AnimateLCM
│
├── controlnet/
│   ├── control_v1p_sd15_qrcode_monster_v2.safetensors
│   │   ← 节点: ControlNetLoaderAdvanced（ControlNet 结构控制）
│   │   ← 下载: https://huggingface.co/monster-labs/control_v1p_sd15_qrcode_monster
│   └── v3_sd15_sparsectrl_rgb.ckpt
│       ← 节点: ACN_SparseCtrlLoaderAdvanced（稀疏控制模型）
│       ← 下载: https://huggingface.co/guoyww/animatediff
│
└── ipadapter/
    └── （由 IPAdapterUnifiedLoader 自动加载，preset: PLUS high strength）
        ← 节点: IPAdapterUnifiedLoader + IPAdapterBatch + PrepImageForClipVision
        ← 需要安装 ComfyUI_IPAdapter_plus 插件后按插件说明放置模型
        ← 插件地址: https://github.com/cubiq/ComfyUI_IPAdapter_plus
```

> **音频分离模型**：`Load Audio Separation Model` 节点使用 `Hybrid Demucs`，由 `ComfyUI-Audio` 插件在首次运行时自动下载，无需手动放置。

#### 1.4 启动 ComfyUI

**macOS / Linux：**

```bash
cd /Users/coco/coco-code/ComfyUI
python main.py
```

**Windows 便携版：**

```
双击运行: run_nvidia_gpu.bat
```

启动成功后验证：

```bash
curl http://localhost:8188/system_stats
# 应返回 JSON，包含 system 信息
```

> 浏览器打开 `http://localhost:8188` 可以看到 ComfyUI 的节点编辑界面。

---

### 第二步：导入 workflow JSON 并在 ComfyUI 中手动验证

#### 2.1 导入 workflow

1. 打开 `http://localhost:8188`
2. 点击右上角菜单 → **Load** → 选择文件：

```
ComfyUI/user/default/workflows/i2v-final.json
```

3. 界面上会显示完整的节点图。

#### 2.2 手动配置测试素材

在 ComfyUI 界面中找到以下节点并手动设置：

| 节点类型 | 需要设置的字段 | 说明 |
|----------|---------------|------|
| `LoadAudio` | `audio` | 选择一个 `.mp3` / `.wav` 文件，放到 `ComfyUI/input/` 目录 |
| `LoadImage`（共 4 个） | `image` | 选择 4 张图片，放到 `ComfyUI/input/` 目录 |
| `INTConstant` "Number of Frames" | `value` | 建议先设置小值如 `24` 快速验证 |
| `INTConstant` "Width Animation" | `value` | 例如 `384` |
| `INTConstant` "Height Animation" | `value` | 例如 `384` |
| `FloatConstant` "Frames per second" | `value` | 例如 `16` |

#### 2.3 运行 workflow 验证

点击 **Queue Prompt** 运行，观察：

```
✅ 节点图逐步变绿 → 生成进行中
✅ 完成后在 ComfyUI/output/ 目录出现 .mp4 文件
✅ 界面右侧 History 面板显示 completed
```

如果报错（节点变红），常见原因：
- 缺少自定义节点 → 回到 1.2 安装对应节点
- 模型文件缺失 → 检查 `models/` 目录
- 音频/图片路径不存在 → 确保文件已放入 `input/`

> **这一步成功后**，说明 ComfyUI + workflow 环境正常，再继续第三步。

---

### 第三步：安装 VJ API 依赖并启动服务

#### 3.1 安装依赖

**macOS / Linux（使用虚拟环境）：**

```bash
cd /Users/coco/coco-code/ComfyUI/vj

# 创建虚拟环境（首次）
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

`requirements.txt` 内容：

```
Flask==3.0.0
flask-cors==4.0.0
requests==2.31.0
websocket-client==1.7.0
```

**Windows（便携版 Python）：**

```bat
cd ComfyUI\vj
start_vj_api.bat   ← 脚本会自动检查并安装依赖，直接运行即可
```

#### 3.2 检查并修改配置

打开 `ComfyUI/vj/config.json`，按实际环境修改：

```json
{
  "comfyui": {
    "url": "http://127.0.0.1:8188",
    "ws_url": "ws://127.0.0.1:8188/ws"
  },
  "api": {
    "host": "0.0.0.0",
    "port": 5002,
    "debug": true
  },
  "paths": {
    "workflow_template": "user/default/workflows/i2v-final.json",
    "input_dir": "input",
    "output_dir": "output"
  },
  "limits": {
    "num_frames_min": 10,
    "num_frames_max": 5000,
    "width_min": 64,
    "width_max": 2048,
    "height_min": 64,
    "height_max": 2048,
    "fps_min": 8,
    "fps_max": 30,
    "max_images": 10
  },
  "timeout": {
    "task_execution": 6000
  }
}
```

> 如果 ComfyUI 运行在另一台机器上，修改 `comfyui.url` 为对应 IP。  
> 如果需要更改 VJ API 端口，修改 `api.port`（前端的 `COMFYUI_API_BASE` 也要同步修改）。

#### 3.3 启动 VJ API 服务

**macOS / Linux：**

```bash
cd /Users/coco/coco-code/ComfyUI/vj
source venv/bin/activate
./start_vj_api.sh
```

**Windows：**

```bat
双击运行 ComfyUI\vj\start_vj_api.bat
```

启动成功后验证：

```bash
curl http://localhost:5002/health
# 应返回: {"status": "healthy", "comfyui": "running", "tasks_count": 0}
```

---

### 第四步：安装并启动前端

#### 4.1 安装 Node.js（首次）

前往 `https://nodejs.org/` 下载 LTS 版本安装。

验证安装：

```bash
node --version   # 应显示 v18 或以上
npm --version
```

#### 4.2 安装前端依赖

```bash
cd /Users/coco/coco-code/vj-disp-fe
npm install
```

#### 4.3 配置环境变量

在 `vj-disp-fe/` 目录下创建 `.env.local` 文件：

```env
# VJ API 地址（如果改了端口，同步修改这里）
COMFYUI_API_BASE=http://localhost:5002/api

# ComfyUI 输出目录的本地绝对路径
# macOS / Linux:
COMFYUI_OUTPUT_BASE=/Users/coco/coco-code/ComfyUI/output

# Windows 示例:
# COMFYUI_OUTPUT_BASE=C:\Users\admin\Downloads\ComfyUI_windows_portable\ComfyUI\output
```

> `COMFYUI_OUTPUT_BASE` 用于把视频文件通过 HTTP 代理给浏览器，不配置的话视频无法在页面上播放。

#### 4.4 启动前端

**开发模式（推荐调试时使用）：**

```bash
cd /Users/coco/coco-code/vj-disp-fe
npm run dev
```

**生产模式（正式使用）：**

```bash
npm run build
npm run start
```

**Windows 一键启动：**

```
双击 vj-disp-fe\🚀一键启动.bat
```

启动成功后打开浏览器访问：

```
http://localhost:3000
```

---

### 第五步：端到端验证

三个服务全部启动后，按以下流程验证整体是否通：

```
1. 打开 http://localhost:3000
2. 点击「开始创作」进入创作空间
3. 上传一段音频（支持 mp3/wav/flac）
4. 选择音乐片段（拖动选区）
5. 选择一个风格（public/template/ 下的文件夹）
6. 点击「生成画面」
7. 等待进度条，完成后跳转播放页或在「我的作品」查看
```

如果视频正常播放，说明全链路打通。

---

### 常见问题速查

| 现象 | 可能原因 | 解决方法 |
|------|----------|----------|
| VJ API 启动时提示 `ComfyUI 未运行` | ComfyUI 没有先启动 | 先执行第一步启动 ComfyUI |
| 任务一直 `queued` | workflow JSON 有节点缺失 | 回到第二步在 ComfyUI UI 中手动跑一次 |
| 视频无法在页面播放 | `COMFYUI_OUTPUT_BASE` 未配置 | 检查 `.env.local` 路径是否正确且重启前端 |
| 上传失败 `无法连接 ComfyUI 服务` | VJ API 没有启动 | 执行第三步启动 VJ API |
| workflow 节点变红报错 | 缺少自定义节点或模型 | 在 ComfyUI-Manager 中安装缺失节点 |
| Windows 端口冲突 | 3000 / 5002 / 8188 被占用 | 修改对应服务端口，并同步更新环境变量 |

---

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

## 🧭 三服务联动总览（`ComfyUI` + `@ComfyUI/vj` + `@vj-disp-fe`）

### 1) 组件职责

- `ComfyUI`（算法端）：负责模型执行与工作流推理，默认监听 `:8188`，并提供 `/prompt`、`/history/{prompt_id}`、`/system_stats`、`/interrupt` 等 API。
- `@ComfyUI/vj`（服务端）：`video_generation_api.py`，负责接收参数、校验、加载并改写 workflow JSON、提交到 ComfyUI、轮询任务、管理并持久化任务状态。
- `@vj-disp-fe`（前端）：Next.js 页面与 `/api/comfyui/*` 代理层，负责调用 `@ComfyUI/vj`、转换视频 URL 并展示任务结果。

### 2) 核心结构（本仓库相关）

```text
ComfyUI/
├── main.py                             # ComfyUI 启动入口（默认 :8188）
├── input/                              # 输入文件目录（audio、images）
├── output/                             # 输出文件目录（video）
├── user/default/workflows/              # workflow JSON 目录（如 i2v-final.json）
└── vj/
    ├── video_generation_api.py          # Flask API（:5002）
    ├── config.json                      # 服务端配置
    ├── requirements.txt
    ├── task_persistence.py              # 任务落盘
    ├── data/tasks.json                  # 任务存储
    ├── start_vj_api.sh / start_vj_api.bat
    └── README.md（本说明）

vj-disp-fe/
├── app/api/comfyui/
│   ├── upload/route.ts
│   ├── generate/route.ts
│   ├── status/[taskId]/route.ts
│   └── output/[...path]/route.ts
├── data/tasks.ts
├── package.json
├── 🚀一键启动.bat / 开发模式启动.bat / 启动服务器.bat
└── ComfyUI配置说明.md
```

### 3) 系统流程图

```mermaid
flowchart LR
    FE[前端页面 @vj-disp-fe]
    Proxy[Next.js API 代理]
    API[VJ API @ComfyUI/vj :5002]
    C[ComfyUI :8188]
    FS[(文件系统 input/output)]

    FE -->|上传音频/图片| Proxy
    Proxy -->|/api/comfyui/upload| API
    API -->|保存文件到| FS

    FE -->|提交生成参数| Proxy
    Proxy -->|POST /api/comfyui/generate| API
    API -->|加载 i2v-final.json 并改写参数| FS
    API -->|POST /prompt| C
    C -->|history/{prompt_id}| API
    API -->|任务状态/输出路径| Proxy
    Proxy --> FE

    FE -->|轮询状态| Proxy
    Proxy -->|GET /api/comfyui/status/{taskId}| API
    FE -->|读取视频| Proxy
    Proxy -->|读取 output 文件| FS
```

### 4) `@ComfyUI/vj` 重点配置与 JSON

- `config.json`
  - `comfyui.url`：上游 ComfyUI 地址（默认 `http://127.0.0.1:8188`）
  - `comfyui.ws_url`：WebSocket 地址（默认 `ws://127.0.0.1:8188/ws`）
  - `paths.workflow_template`：`user/default/workflows/i2v-final.json`
  - `paths.input_dir` / `paths.output_dir`：`input` / `output`
  - `limits`：num_frames、宽高、fps、max_images
  - `api`：`host/port/debug`
  - `timeout.task_execution`：任务超时（秒）
- `requirements.txt`：`Flask`、`flask-cors`、`requests`、`websocket-client`
- `data/tasks.json`：任务持久化，用于重启后恢复任务
- `workflow JSON`：图节点与参数（如 `LoadAudio`、`LoadImage`、`INTConstant`、`FloatConstant`、`VHS_VideoCombine`）  
  `video_generation_api.py` 在运行时会做清理、修正和重连线，支持 4-10 张图片。

```json
{
  "comfyui": { "url": "http://127.0.0.1:8188", "ws_url": "ws://127.0.0.1:8188/ws" },
  "api": { "host": "0.0.0.0", "port": 5002, "debug": true },
  "paths": {
    "workflow_template": "user/default/workflows/i2v-final.json",
    "input_dir": "input",
    "output_dir": "output"
  },
  "limits": {
    "num_frames_min": 10,
    "num_frames_max": 5000,
    "width_min": 64,
    "width_max": 2048,
    "height_min": 64,
    "height_max": 2048,
    "fps_min": 8,
    "fps_max": 30,
    "max_images": 10
  },
  "timeout": { "task_execution": 6000 }
}
```

### 5) `@vj-disp-fe` 关键环境变量

- `COMFYUI_API_BASE`（默认 `http://localhost:5002/api`）
- `COMFYUI_OUTPUT_BASE`（前端读取输出文件路径基址）

示例 `.env.local`：

```env
COMFYUI_API_BASE=http://localhost:5002/api
COMFYUI_OUTPUT_BASE=/Users/coco/coco-code/ComfyUI/output
```

### 6) 启动顺序（建议）

1. 启动 ComfyUI  
```bash
cd /Users/coco/coco-code/ComfyUI
python main.py
```
确认 `curl http://localhost:8188/system_stats`

2. 启动 VJ API  
```bash
cd /Users/coco/coco-code/ComfyUI/vj
./start_vj_api.sh         # macOS / Linux
# Windows: start_vj_api.bat
```
确认 `curl http://localhost:5002/health`

3. 启动前端  
```bash
cd /Users/coco/coco-code/vj-disp-fe
npm run dev
```
打开 `http://localhost:3000`

### 7) 端口与关键路由

- Frontend：`3000`
- VJ API：`5002`
- ComfyUI：`8188`
- VJ API 上传：`/api/upload-image`、`/api/upload-audio`、`/api/generate-video`
- VJ API 查询：`/api/tasks/{task_id}`、`/api/tasks/{task_id}/download`、`/health`
- 前端代理：`/api/comfyui/upload`、`/api/comfyui/generate`、`/api/comfyui/status/{taskId}`、`/api/comfyui/output/[...path]`

### 8) 任务状态

`queued -> processing -> completed / failed / cancelled / timeout`  
任务信息最终写入 `tasks.json`，启动时执行恢复逻辑（`restore_tasks_from_disk`）。

----

**Happy Coding! 🎉**
