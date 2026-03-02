# 🎬 VJ 视频生成 API 服务

基于 ComfyUI 的音频反应式视频生成服务，提供 RESTful API 供前端调用。

---

## 📚 文档索引

| 文件 | 内容 |
|------|------|
| 本文档（`README.md`） | 架构总览、部署流程、API 端点、配置说明 |
| `VJ_API运行成功.md` | 启动成功摘要与快速验证命令 |
| `VJ_API日志说明.md` | 日志分类与排障方法 |
| `config.json` | 服务配置（地址、端口、路径、参数限制） |
| `task_persistence.py` | 任务落盘与重启恢复逻辑 |
| `start_vj_api.sh / .bat` | 启动脚本 |
| `vj-disp-fe/ComfyUI配置说明.md` | 前端 `COMFYUI_OUTPUT_BASE` 配置说明 |
| `vj-disp-fe/Windows使用说明.md` | Windows 前端启动与常见问题 |

---

## 🧩 整体模块图（前端 → 服务端 → 算法端）

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                       @vj-disp-fe  前端  :3000                               │
│                                                                              │
│   浏览器页面                                                                  │
│   ├── 上传音乐/图片 ──→ POST /api/comfyui/upload                              │
│   │                      body: { file, taskId, fileType: "audio"|"image" }  │
│   │                                                                          │
│   ├── 生成视频     ──→ POST /api/comfyui/generate                            │
│   │                      body: { audioPath, images[], numFrames,             │
│   │                              width, height, fps }                        │
│   │                                                                          │
│   ├── 轮询状态     ──→ GET  /api/comfyui/status/{taskId}                     │
│   │                      返回: { status, videoPath, elapsedSeconds }         │
│   │                                                                          │
│   └── 播放视频     ──→ GET  /api/comfyui/output/[...path]                    │
│                         读取磁盘文件流返回浏览器                              │
│                         [配置] COMFYUI_OUTPUT_BASE = ComfyUI/output 绝对路径 │
└─────────────────────────────────┬────────────────────────────────────────────┘
                                  │  [配置] COMFYUI_API_BASE=http://localhost:5002/api
                                  ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    @ComfyUI/vj  任务服务  :5002                               │
│                    video_generation_api.py (Flask)                           │
│                                                                              │
│  ┌─ 文件上传 ──────────────────────────────────────────────────────────────┐ │
│  │  POST /api/upload-audio                                                 │ │
│  │       body: multipart/form-data(file) 或 JSON { filename, data(base64)} │ │
│  │       → 保存到 input/{task_id}/filename                                 │ │
│  │  POST /api/upload-image    (同上，支持 jpg/png/webp/gif/bmp)            │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─ 视频生成 ──────────────────────────────────────────────────────────────┐ │
│  │  POST /api/generate-video                                               │ │
│  │       body: {                                                           │ │
│  │         audio_path: string   ← 必填，相对 input/ 或绝对路径             │ │
│  │         images: string[]     ← 必填，4~10 张，相对 input/               │ │
│  │         num_frames: int      ← 默认 480  [配置] config.json limits      │ │
│  │         width: int           ← 默认 480  [配置] config.json limits      │ │
│  │         height: int          ← 默认 300  [配置] config.json limits      │ │
│  │         fps: float           ← 默认 16   [配置] config.json limits      │ │
│  │       }                                                                 │ │
│  │    1. 加载 workflow JSON  [配置] paths.workflow_template                │ │
│  │    2. 清洗注释节点 / 修正 KSampler/LoRA 错误参数                        │ │
│  │    3. 重写节点参数:                                                     │ │
│  │         LoadAudio            ← audio_path                               │ │
│  │         LoadImage × N        ← images[]（动态扩展到 4-10 张）           │ │
│  │         INTConstant "Number of Frames" ← num_frames                    │ │
│  │         INTConstant "Width/Height Animation" ← width, height            │ │
│  │         FloatConstant "Frames per second" ← fps                         │ │
│  │         VHS_VideoCombine.filename_prefix ← "vj/{task_id}_"             │ │
│  │    4. POST /prompt 到 ComfyUI → 返回 task_id                            │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─ 任务管理 ──────────────────────────────────────────────────────────────┐ │
│  │  GET    /api/tasks/{task_id}          → 查状态 / video_path            │ │
│  │  GET    /api/tasks?limit&status       → 任务列表                        │ │
│  │  GET    /api/tasks/{task_id}/download → 直接下载 mp4                    │ │
│  │  DELETE /api/tasks/{task_id}          → 取消 + 通知 ComfyUI /interrupt  │ │
│  │  GET    /health                       → { status, comfyui, tasks_count }│ │
│  │                                                                         │ │
│  │  任务状态: queued → processing → completed / failed / cancelled         │ │
│  │  持久化:  data/tasks.json   [重启时自动恢复 queued/processing 任务]     │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─ 配置文件 config.json ──────────────────────────────────────────────────┐ │
│  │  comfyui.url            = http://127.0.0.1:8188                        │ │
│  │  comfyui.ws_url         = ws://127.0.0.1:8188/ws                       │ │
│  │  api.port               = 5002                                          │ │
│  │  paths.workflow_template= user/default/workflows/i2v-final.json        │ │
│  │  paths.input_dir        = input                                         │ │
│  │  paths.output_dir       = output                                        │ │
│  │  limits.*               = 参数合法性边界                                │ │
│  │  timeout.task_execution = 6000  (秒)                                   │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────┬────────────────────────────────────────────┘
                                  │  固定: http://127.0.0.1:8188
                                  ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                       ComfyUI  算法端  :8188                                 │
│                       python main.py                                         │
│                                                                              │
│   POST /prompt          ← 提交 workflow { client_id, prompt }               │
│   GET  /history/{id}    ← 轮询状态与输出文件（polling 间隔 2s）             │
│   GET  /system_stats    ← 健康检查                                           │
│   POST /interrupt       ← 中止当前任务                                       │
│                                                                              │
│   Workflow JSON (i2v-final.json) 关键节点:                                   │
│   ├── LoadAudio              音频输入                                        │
│   ├── LoadImage × 4-10       图片输入（动态扩展）                            │
│   ├── ImageBatchMulti(376)   批量图片合并                                    │
│   ├── INTConstant            帧数 / 宽度 / 高度                              │
│   ├── FloatConstant          FPS                                             │
│   ├── IPAdapterUnifiedLoader 图像风格（PLUS high strength）                  │
│   ├── ACN_SparseCtrlLoader   稀疏控制                                        │
│   ├── ADE_LoadAnimateDiff    运动模型                                        │
│   ├── KSampler               采样器                                          │
│   └── VHS_VideoCombine(410)  输出视频 → output/vj/{task_id}__.mp4           │
│                                                                              │
│   input/{task_id}/   ← 上传的音频/图片                                      │
│   output/vj/         ← 生成的视频                                           │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ 从零开始：完整部署流程

> 按顺序执行，每步验证通过后再继续。

---

### 第一步：安装并启动 ComfyUI

#### 1.1 下载

**Windows 便携版（推荐）**

```
下载: https://github.com/comfyanonymous/ComfyUI/releases/latest/download/ComfyUI_windows_portable_nvidia.7z
解压到本地，例如: D:\ComfyUI_windows_portable\ComfyUI
使用内置 python_embeded\python.exe，无需单独安装 Python
```

**macOS / Linux**

```bash
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
pip install torch torchvision torchaudio
pip install -r requirements.txt
```

#### 1.2 安装自定义节点

先安装 ComfyUI-Manager：

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Comfy-Org/ComfyUI-Manager.git
```

重启 ComfyUI 后，浏览器 UI → **Manager** → **Install Missing Custom Nodes**，安装以下节点：

| 插件 | 提供的节点 |
|------|-----------|
| `comfyui-videohelpersuite` | `VHS_VideoCombine` |
| `ComfyUI-AnimateDiff-Evolved` | `ADE_*` 系列节点 |
| `ComfyUI-Audio` | `LoadAudio`、`Audio Analysis`、`Load Audio Separation Model` |
| `ComfyUI_IPAdapter_plus` | `IPAdapterUnifiedLoader`、`IPAdapterBatch` |
| `ComfyUI-Advanced-ControlNet` | `ACN_SparseCtrl*` 系列节点 |

#### 1.3 准备模型文件

以下为 `i2v-final.json` 实际引用的模型，按目录放置：

```
ComfyUI/models/
├── checkpoints/
│   └── DreamShaper_8_pruned.safetensors
│       节点: CheckpointLoaderSimple
│       下载: https://civitai.com/models/4384/dreamshaper
│
├── vae/
│   └── vae-ft-mse-840000-ema-pruned.safetensors
│       节点: VAELoader
│       下载: https://huggingface.co/stabilityai/sd-vae-ft-mse-original
│
├── loras/
│   ├── AnimateLCM_sd15_t2v_lora.safetensors
│   │   节点: LoraLoaderModelOnly（LCM 加速 LoRA）
│   │   下载: https://huggingface.co/wangfuyun/AnimateLCM
│   └── v3_sd15_adapter.ckpt
│       节点: LoraLoaderModelOnly（SparseCtrl Adapter）
│       下载: https://huggingface.co/guoyww/animatediff
│
├── animatediff_models/
│   └── AnimateLCM_sd15_t2v.ckpt
│       节点: ADE_LoadAnimateDiffModel
│       下载: https://huggingface.co/wangfuyun/AnimateLCM
│
├── controlnet/
│   ├── control_v1p_sd15_qrcode_monster_v2.safetensors
│   │   节点: ControlNetLoaderAdvanced
│   │   下载: https://huggingface.co/monster-labs/control_v1p_sd15_qrcode_monster
│   └── v3_sd15_sparsectrl_rgb.ckpt
│       节点: ACN_SparseCtrlLoaderAdvanced
│       下载: https://huggingface.co/guoyww/animatediff
│
└── ipadapter/
    按 ComfyUI_IPAdapter_plus 插件说明放置
    插件地址: https://github.com/cubiq/ComfyUI_IPAdapter_plus
```

> `Hybrid Demucs` 音频分离模型由 `ComfyUI-Audio` 首次运行时自动下载，无需手动放置。

#### 1.4 启动 ComfyUI

**macOS / Linux：**

```bash
cd ComfyUI
python main.py
```

**Windows 便携版：**

```
双击 run_nvidia_gpu.bat
```

**验证：**

```bash
curl http://localhost:8188/system_stats
# 返回含 system 字段的 JSON 即为成功
```

---

### 第二步：导入 workflow 并在 ComfyUI 中手动验证

1. 浏览器打开 `http://localhost:8188`
2. 菜单 → **Load** → 选择 `ComfyUI/user/default/workflows/i2v-final.json`
3. 手动配置以下节点用于测试：

| 节点 | 字段 | 建议值 |
|------|------|--------|
| `LoadAudio` | `audio` | 放一个 `.mp3` 到 `input/`，选中它 |
| `LoadImage` × 4 | `image` | 放 4 张图到 `input/`，分别选中 |
| `INTConstant` "Number of Frames" | `value` | `24`（先用小值快速验证） |
| `INTConstant` "Width Animation" | `value` | `384` |
| `INTConstant` "Height Animation" | `value` | `384` |
| `FloatConstant` "Frames per second" | `value` | `16` |

4. 点击 **Queue Prompt**，等待节点变绿、`output/` 目录出现 `.mp4` 文件。

> 节点变红时：缺少节点 → 回到 1.2 安装；模型缺失 → 回到 1.3 放置模型。
>
> **此步成功后**，说明 ComfyUI + workflow 环境正常，再继续第三步。

---

### 第三步：安装 VJ API 依赖并启动

#### 3.1 安装依赖

**macOS / Linux：**

```bash
cd ComfyUI/vj
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Windows：** 直接运行 `start_vj_api.bat`，脚本自动检测并安装依赖。

#### 3.2 配置 `config.json`

关键字段说明（完整文件见 `ComfyUI/vj/config.json`）：

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `comfyui.url` | `http://127.0.0.1:8188` | ComfyUI 服务地址，多机部署时改为对应 IP |
| `api.port` | `5002` | VJ API 端口，改后需同步更新前端 `COMFYUI_API_BASE` |
| `paths.workflow_template` | `user/default/workflows/i2v-final.json` | workflow 模板路径（相对 ComfyUI 根目录） |
| `limits.*` | 见文件 | 参数合法性边界 |
| `timeout.task_execution` | `6000` | 单任务最长执行秒数 |

#### 3.3 启动

**macOS / Linux：**

```bash
cd ComfyUI/vj
source venv/bin/activate
./start_vj_api.sh
```

**Windows：**

```
双击 start_vj_api.bat
```

**验证：**

```bash
curl http://localhost:5002/health
# 返回 {"status": "healthy", "comfyui": "running", ...} 即为成功
```

---

### 第四步：安装并启动前端

#### 4.1 前置：安装 Node.js

下载 LTS 版本：`https://nodejs.org/`，要求 v18+。

#### 4.2 安装依赖并配置

```bash
cd vj-disp-fe
npm install
```

创建 `vj-disp-fe/.env.local`：

```env
# VJ API 地址（端口与 config.json api.port 保持一致）
COMFYUI_API_BASE=http://localhost:5002/api

# ComfyUI output 目录的本地绝对路径（用于视频文件代理）
COMFYUI_OUTPUT_BASE=/Users/coco/coco-code/ComfyUI/output
# Windows 示例:
# COMFYUI_OUTPUT_BASE=C:\Users\admin\Downloads\ComfyUI_windows_portable\ComfyUI\output
```

> `COMFYUI_OUTPUT_BASE` 不配置会导致视频无法在页面播放。详见 `vj-disp-fe/ComfyUI配置说明.md`。

#### 4.3 启动

```bash
# 开发模式
npm run dev

# 生产模式
npm run build && npm run start
```

**Windows 一键启动：** 双击 `🚀一键启动.bat`

访问 `http://localhost:3000`

---

### 第五步：端到端验证

```
1. 打开 http://localhost:3000
2. 「开始创作」→ 上传音频 → 选择片段 → 选择风格 → 「生成画面」
3. 等待进度条完成 → 在「我的作品」查看视频
```

---

### 常见问题速查

| 现象 | 原因 | 解决 |
|------|------|------|
| VJ API 提示 `ComfyUI 未运行` | ComfyUI 未启动 | 先完成第一步 |
| 任务一直 `queued` | workflow 节点或模型缺失 | 回到第二步在 ComfyUI UI 中手动跑一次 |
| 视频无法在页面播放 | `COMFYUI_OUTPUT_BASE` 未配置或路径错误 | 检查 `.env.local`，修改后重启前端 |
| 上传失败 `无法连接 ComfyUI 服务` | VJ API 未启动 | 完成第三步 |
| workflow 节点变红 | 缺少自定义节点或模型 | ComfyUI-Manager → Install Missing Custom Nodes |
| 端口冲突 | 3000 / 5002 / 8188 被占用 | 修改对应端口，同步更新 `config.json` 和 `.env.local` |

---

## ⚙️ API 端点速览

> 详细参数和错误码见 `VJ_API运行成功.md`。

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/api/upload-image` | 上传图片（multipart 或 base64） |
| POST | `/api/upload-audio` | 上传音频（multipart 或 base64） |
| POST | `/api/generate-video` | 提交生成任务，返回 `task_id` |
| GET | `/api/tasks/{task_id}` | 查询状态，完成后返回 `video_path` |
| GET | `/api/tasks` | 列出所有任务，支持 `?limit&status` 过滤 |
| GET | `/api/tasks/{task_id}/download` | 直接下载 mp4 |
| DELETE | `/api/tasks/{task_id}` | 取消任务 |

### `POST /api/generate-video` 参数

| 参数 | 类型 | 必填 | 默认值 | 限制（config.json） |
|------|------|------|--------|---------------------|
| `audio_path` | string | ✅ | — | 相对 `input/` 或绝对路径 |
| `images` | string[] | ✅ | — | 4~10 张，相对 `input/` |
| `num_frames` | int | ❌ | 480 | 10 ~ 5000 |
| `width` | int | ❌ | 480 | 64 ~ 2048 |
| `height` | int | ❌ | 300 | 64 ~ 2048 |
| `fps` | float | ❌ | 16 | 8 ~ 30 |

---

## 🔧 技术架构

- **Flask** + **threading**：异步任务处理
- **task_persistence.py**：任务落盘，重启后自动恢复 `queued/processing` 状态的任务
- **workflow 动态改写**：运行时注入音频/图片/尺寸参数，无需修改 JSON 文件
- **文件隔离**：每个 task 使用独立子目录 `input/{task_id}/`，避免冲突

---

## 📁 目录结构

```
ComfyUI/
├── main.py
├── input/                              上传的音频 / 图片
├── output/vj/                          生成的视频
├── user/default/workflows/
│   ├── i2v-final.json                  当前使用的 workflow 模板
│   └── i2v-low-res.json               低分辨率备用 workflow
└── vj/
    ├── video_generation_api.py         Flask API 主程序
    ├── config.json                     服务配置
    ├── requirements.txt
    ├── task_persistence.py
    ├── data/tasks.json                 任务持久化
    ├── start_vj_api.sh / .bat
    ├── tests/                          测试脚本
    └── README.md

vj-disp-fe/
├── app/api/comfyui/                    前端代理接口
│   ├── upload/route.ts
│   ├── generate/route.ts
│   ├── status/[taskId]/route.ts
│   └── output/[...path]/route.ts
├── data/tasks.ts                       前端任务队列管理
├── public/template/                    风格模板图片（按文件夹分类）
├── public/music/                       DEMO 音乐
├── .env.local                          环境变量配置
└── 🚀一键启动.bat / 开发模式启动.bat
```

---

**Happy Coding! 🎉**
