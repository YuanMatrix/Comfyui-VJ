#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VJ 视频生成 API 服务

通过简单的 RESTful API 调用 ComfyUI 生成音频反应式视频
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import json
import requests
import time
import os
import uuid
import websocket
from datetime import datetime
from typing import Dict, Optional, List
import threading
from pathlib import Path

# 添加当前目录到 Python 路径，以支持相对导入
import sys
CURRENT_DIR = Path(__file__).parent
if str(CURRENT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR.parent))

from vj.task_persistence import TaskPersistenceManager, recover_task_status

app = Flask(__name__)
CORS(app)

# =============================================================================
# 请求日志中间件
# =============================================================================

@app.before_request
def log_request_info():
    """记录每个请求的详细信息"""
    print(f"\n{'='*60}")
    print(f"📥 收到请求: {request.method} {request.path}")
    print(f"   来源: {request.remote_addr}")
    print(f"   Content-Type: {request.content_type}")
    
    # 打印查询参数
    if request.args:
        print(f"   查询参数: {dict(request.args)}")
    
    # 打印表单数据
    if request.form:
        print(f"   表单数据: {dict(request.form)}")
    
    # 打印 JSON 数据
    if request.is_json:
        try:
            json_data = request.get_json()
            # 隐藏敏感信息
            safe_data = {k: v if k not in ['data', 'password'] else '***' for k, v in json_data.items()}
            print(f"   JSON 数据:")
            print(json.dumps(safe_data, indent=4, ensure_ascii=False))
        except:
            pass
    
    # 打印文件
    if request.files:
        print(f"   上传文件: {list(request.files.keys())}")
        for key, file in request.files.items():
            print(f"      - {key}: {file.filename} ({file.content_type})")
    
    print(f"{'='*60}")


@app.after_request
def log_response_info(response):
    """记录响应信息"""
    status_code = response.status_code
    
    # 对于错误响应，打印响应内容
    if status_code >= 400:
        print(f"📤 响应: {status_code} ❌")
        try:
            if response.is_json:
                response_data = response.get_json()
                print(f"   错误信息: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
        except:
            pass
    else:
        print(f"📤 响应: {status_code} ✅")
    
    return response


@app.errorhandler(404)
def not_found_error(error):
    """404 错误处理器"""
    print(f"\n❌ 404 错误:")
    print(f"   请求路径: {request.method} {request.path}")
    print(f"   可用端点:")
    for rule in app.url_map.iter_rules():
        if rule.endpoint != 'static':
            print(f"      {', '.join(rule.methods)} {rule.rule}")
    
    return jsonify({
        "success": False,
        "error": "端点不存在",
        "path": request.path,
        "method": request.method,
        "message": f"未找到路径: {request.method} {request.path}"
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """500 错误处理器"""
    print(f"\n❌ 500 错误:")
    print(f"   请求路径: {request.method} {request.path}")
    print(f"   错误信息: {error}")
    import traceback
    traceback.print_exc()
    
    return jsonify({
        "success": False,
        "error": "服务器内部错误",
        "message": str(error)
    }), 500

# =============================================================================
# 配置
# =============================================================================

# 加载配置文件
CONFIG_FILE = Path(__file__).parent / "config.json"
if CONFIG_FILE.exists():
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        CONFIG = json.load(f)
else:
    CONFIG = {}

# ComfyUI 服务地址
COMFYUI_URL = CONFIG.get('comfyui', {}).get('url', "http://127.0.0.1:8188")
COMFYUI_WS_URL = CONFIG.get('comfyui', {}).get('ws_url', "ws://127.0.0.1:8188/ws")

# 路径配置
BASE_DIR = Path(__file__).parent.parent  # ComfyUI 根目录
WORKFLOW_TEMPLATE = BASE_DIR / CONFIG.get('paths', {}).get('workflow_template', 'user/default/workflows/i2v-low-res.json')
INPUT_DIR = BASE_DIR / CONFIG.get('paths', {}).get('input_dir', 'input')
OUTPUT_DIR = BASE_DIR / CONFIG.get('paths', {}).get('output_dir', 'output')

# 任务存储目录
TASK_STORAGE_DIR = Path(__file__).parent / 'data'
TASK_STORAGE_FILE = TASK_STORAGE_DIR / 'tasks.json'

# 初始化任务持久化管理器
task_persistence = TaskPersistenceManager(TASK_STORAGE_FILE)

# 参数限制（从配置读取）
LIMITS = CONFIG.get('limits', {})
NUM_FRAMES_MIN = LIMITS.get('num_frames_min', 1)
NUM_FRAMES_MAX = LIMITS.get('num_frames_max', 2000)

# 宽度和高度支持两种配置方式：
# 1. width_options/height_options: 只允许特定值（旧方式）
# 2. width_min/width_max, height_min/height_max: 允许范围内任意值（新方式）
if 'width_options' in LIMITS:
    WIDTH_OPTIONS = LIMITS['width_options']
    WIDTH_MIN = WIDTH_MAX = None
else:
    WIDTH_MIN = LIMITS.get('width_min', 64)
    WIDTH_MAX = LIMITS.get('width_max', 2048)
    WIDTH_OPTIONS = None

if 'height_options' in LIMITS:
    HEIGHT_OPTIONS = LIMITS['height_options']
    HEIGHT_MIN = HEIGHT_MAX = None
else:
    HEIGHT_MIN = LIMITS.get('height_min', 64)
    HEIGHT_MAX = LIMITS.get('height_max', 2048)
    HEIGHT_OPTIONS = None

FPS_MIN = LIMITS.get('fps_min', 8)
FPS_MAX = LIMITS.get('fps_max', 60)

# 任务存储（内存中，生产环境建议用数据库）
tasks = {}
task_lock = threading.Lock()

# =============================================================================
# 任务恢复
# =============================================================================

def restore_tasks_from_disk():
    """从磁盘恢复任务到内存"""
    global tasks
    
    print("\n" + "=" * 60)
    print("🔄 正在恢复之前的任务...")
    print("=" * 60)
    
    # 加载所有任务
    stored_tasks = task_persistence.load_all_tasks()
    
    if not stored_tasks:
        print("✅ 没有需要恢复的任务")
        return
    
    # 统计
    total = len(stored_tasks)
    restored = 0
    completed = 0
    failed = 0
    
    with task_lock:
        for task_id, task_data in stored_tasks.items():
            status = task_data.get('status')
            prompt_id = task_data.get('prompt_id')
            
            # 恢复到内存
            tasks[task_id] = task_data
            
            # 对于未完成的任务，尝试从 ComfyUI 恢复状态
            if status in ['queued', 'processing'] and prompt_id:
                print(f"\n📋 恢复任务: {task_id}")
                print(f"   原状态: {status}")
                print(f"   Prompt ID: {prompt_id}")
                
                # 查询 ComfyUI 状态
                recovered_status = recover_task_status(COMFYUI_URL, prompt_id)
                
                if recovered_status:
                    new_status = recovered_status.get('status')
                    print(f"   新状态: {new_status}")
                    
                    # 更新状态
                    tasks[task_id]['status'] = new_status
                    
                    if new_status == 'completed':
                        # 恢复输出文件信息
                        outputs = recovered_status.get('outputs', {})
                        if '410' in outputs:
                            videos = outputs['410'].get('gifs', [])
                            output_files = []
                            for video in videos:
                                video_path = OUTPUT_DIR / video['subfolder'] / video['filename']
                                if video_path.exists():
                                    output_files.append({
                                        "filename": video['filename'],
                                        "subfolder": video['subfolder'],
                                        "type": video.get('type', 'output'),
                                        "path": str(video_path)
                                    })
                            
                            tasks[task_id]['output_files'] = output_files
                            tasks[task_id]['completed_at'] = datetime.now().isoformat()
                            completed += 1
                    
                    elif new_status == 'failed':
                        tasks[task_id]['error'] = recovered_status.get('error', 'Unknown error')
                        failed += 1
                    
                    # 保存更新后的状态
                    task_persistence.save_task(task_id, tasks[task_id])
                    restored += 1
                else:
                    print(f"   ⚠️  无法从 ComfyUI 恢复状态，保持原状态")
            
            elif status in ['completed', 'failed', 'cancelled']:
                # 已完成的任务直接恢复
                restored += 1
    
    print(f"\n" + "=" * 60)
    print(f"📊 任务恢复完成:")
    print(f"   总任务数: {total}")
    print(f"   已恢复: {restored}")
    print(f"   新完成: {completed}")
    print(f"   新失败: {failed}")
    print("=" * 60 + "\n")


def persist_task(task_id: str):
    """将任务持久化到磁盘"""
    with task_lock:
        if task_id in tasks:
            task_persistence.save_task(task_id, tasks[task_id])

# =============================================================================
# 工具函数
# =============================================================================

def load_workflow_template() -> dict:
    """
    加载 workflow 模板并清理不必要的节点
    
    会自动移除注释节点和其他不参与计算的辅助节点
    """
    with open(WORKFLOW_TEMPLATE, 'r', encoding='utf-8') as f:
        workflow = json.load(f)
    
    # 过滤掉注释节点和其他不参与计算的节点
    # 这些节点在 ComfyUI UI 中用于显示说明，但在 API 执行时不需要
    SKIP_NODE_TYPES = {
        'MarkdownNote',     # Markdown 注释节点
        'Note',             # 普通注释节点
        'PrimitiveNode',    # 原始值节点（某些情况下）
        'Reroute',          # 路由节点（某些情况下）
    }
    
    original_node_count = len(workflow.get('nodes', []))
    
    # 移除注释节点
    if 'nodes' in workflow:
        workflow['nodes'] = [
            node for node in workflow['nodes']
            if node.get('type') not in SKIP_NODE_TYPES
        ]
        
        removed_count = original_node_count - len(workflow['nodes'])
        if removed_count > 0:
            print(f"[INFO] 已移除 {removed_count} 个注释/辅助节点（不影响执行）")
    
    # 修复常见的参数问题
    workflow = fix_workflow_issues(workflow)
    
    return workflow


def fix_workflow_issues(workflow: dict) -> dict:
    """
    修复工作流中的常见问题
    
    1. Repeat Image To Count: count 不能为 0
    2. AnimateDiff LoRA: 确保 LoRA 文件存在
    3. KSampler: 确保参数格式正确，移除 "fixed" 等无效值
    """
    for node in workflow.get('nodes', []):
        node_type = node.get('type')
        
        # 修复 Repeat Image To Count
        if node_type == 'Repeat Image To Count':
            if 'widgets_values' in node:
                if isinstance(node['widgets_values'], list):
                    # count 参数通常是第一个
                    if len(node['widgets_values']) > 0 and node['widgets_values'][0] == 0:
                        node['widgets_values'][0] = 1
                        print(f"[FIX] Node {node['id']}: 修正 count 值从 0 到 1")
                elif isinstance(node['widgets_values'], dict):
                    if node['widgets_values'].get('count') == 0:
                        node['widgets_values']['count'] = 1
                        print(f"[FIX] Node {node['id']}: 修正 count 值从 0 到 1")
        
        # 修复 AnimateDiff LoRA - 使用可用的 LoRA
        elif node_type == 'ADE_AnimateDiffLoRALoader':
            if 'widgets_values' in node:
                if isinstance(node['widgets_values'], dict):
                    lora_name = node['widgets_values'].get('name')
                    if lora_name and 'LiquidAF' in lora_name:
                        # 改用默认的 AnimateLCM LoRA
                        node['widgets_values']['name'] = 'AnimateLCM_sd15_t2v_lora.safetensors'
                        print(f"[FIX] Node {node['id']}: 将 LoRA 改为 AnimateLCM_sd15_t2v_lora.safetensors")
                elif isinstance(node['widgets_values'], list):
                    if len(node['widgets_values']) > 0 and 'LiquidAF' in str(node['widgets_values'][0]):
                        node['widgets_values'][0] = 'AnimateLCM_sd15_t2v_lora.safetensors'
                        print(f"[FIX] Node {node['id']}: 将 LoRA 改为 AnimateLCM_sd15_t2v_lora.safetensors")
        
        # 修复 KSampler - 清理参数列表，移除无效值
        elif node_type == 'KSampler':
            if 'widgets_values' in node and isinstance(node['widgets_values'], list):
                values = node['widgets_values']
                
                # 标准的 KSampler 参数顺序应该是:
                # [seed, steps, cfg, sampler_name, scheduler, denoise]
                # 但有时候会有 "fixed" 等控制字符串混入
                
                # 移除 "fixed" 等控制字符串
                cleaned_values = []
                for i, val in enumerate(values):
                    if val == "fixed" or val == "randomize":
                        print(f"[FIX] Node {node['id']}: 移除无效参数 '{val}' (位置 {i})")
                        continue
                    cleaned_values.append(val)
                
                # 确保至少有6个参数
                if len(cleaned_values) >= 6:
                    seed = cleaned_values[0]
                    steps = cleaned_values[1] if isinstance(cleaned_values[1], int) else 8
                    cfg = cleaned_values[2] if isinstance(cleaned_values[2], (int, float)) else 2.0
                    sampler_name = cleaned_values[3] if isinstance(cleaned_values[3], str) else "euler"
                    scheduler = cleaned_values[4] if isinstance(cleaned_values[4], str) else "sgm_uniform"
                    denoise = cleaned_values[5] if isinstance(cleaned_values[5], (int, float)) else 1.0
                    
                    # 修正无效的 sampler_name
                    if sampler_name == "lcm":
                        sampler_name = "euler"
                        print(f"[FIX] Node {node['id']}: 将 sampler_name 从 'lcm' 改为 'euler'")
                    
                    # 修正无效的 scheduler
                    valid_schedulers = ['simple', 'sgm_uniform', 'karras', 'exponential', 'ddim_uniform', 'beta', 'normal', 'linear_quadratic', 'kl_optimal']
                    if scheduler not in valid_schedulers:
                        scheduler = "sgm_uniform"
                        print(f"[FIX] Node {node['id']}: 将 scheduler 改为 'sgm_uniform'")
                    
                    # 重建参数列表
                    node['widgets_values'] = [seed, steps, cfg, sampler_name, scheduler, denoise]
                    
            elif 'widgets_values' in node and isinstance(node['widgets_values'], dict):
                # Dict格式的处理
                if node['widgets_values'].get('scheduler') == 'lcm':
                    node['widgets_values']['scheduler'] = 'sgm_uniform'
                    print(f"[FIX] Node {node['id']}: 将 scheduler 从 'lcm' 改为 'sgm_uniform'")
                
                if node['widgets_values'].get('sampler_name') == 'lcm':
                    node['widgets_values']['sampler_name'] = 'euler'
                    print(f"[FIX] Node {node['id']}: 将 sampler_name 从 'lcm' 改为 'euler'")
    
    return workflow


def convert_to_api_format(workflow: dict) -> dict:
    """
    将 ComfyUI workflow 转换为 API 格式
    
    从 UI 格式:
    {
        "nodes": [{"id": 520, "type": "LoadAudio", "inputs": [...]}],
        "links": [...]
    }
    
    转换为 API 格式:
    {
        "520": {"class_type": "LoadAudio", "inputs": {...}}
    }
    """
    api_workflow = {}
    
    # 处理节点
    for node in workflow.get('nodes', []):
        node_id = str(node['id'])
        
        # 获取节点类型
        node_type = node.get('type')
        
        # 构建输入
        inputs = {}
        
        # 先添加 widgets_values 的值（作为默认值）
        if 'widgets_values' in node:
            widgets_values = node['widgets_values']
            
            if isinstance(widgets_values, dict):
                # 直接使用 dict 格式的 widgets（这是最可靠的）
                for key, value in widgets_values.items():
                    # 跳过特殊的 UI 相关字段
                    if key not in ['videopreview', 'audiopreview']:
                        inputs[key] = value
            
            elif isinstance(widgets_values, list):
                # 列表格式：按顺序匹配有 widget 的输入
                widget_inputs = [inp for inp in node.get('inputs', []) if 'widget' in inp]
                for i, value in enumerate(widgets_values):
                    if i < len(widget_inputs):
                        input_name = widget_inputs[i]['name']
                        inputs[input_name] = value
        
        # 处理 inputs（连接和 widget 值）- 连接会覆盖 widgets_values
        for input_item in node.get('inputs', []):
            input_name = input_item['name']
            
            # 如果有 link，使用连接（优先级最高）
            if input_item.get('link') is not None:
                # 找到连接的源节点
                link_id = input_item['link']
                source = find_link_source(workflow, link_id)
                if source:
                    inputs[input_name] = [str(source['node_id']), source['slot_index']]
        
        # 构建 API 节点
        api_workflow[node_id] = {
            "class_type": node_type,
            "inputs": inputs
        }
    
    return api_workflow


def find_link_source(workflow: dict, link_id: int) -> Optional[Dict]:
    """查找连接的源节点"""
    for link in workflow.get('links', []):
        if link[0] == link_id:
            return {
                'node_id': link[1],
                'slot_index': link[2]
            }
    return None


def update_workflow_params(workflow: dict, audio_path: str, num_frames: int, 
                          width: int, height: int, fps: float,
                          images: List[str], task_id: str = None) -> dict:
    """
    更新 workflow 中的参数，支持 4-10 张图片
    
    解组后的工作流节点映射:
    - LoadAudio: 音频文件 (根据类型自动查找)
    - 552: INTConstant "Number of Frames" (帧数)
    - 553: FloatConstant "Frames per second" (FPS)
    - 554: INTConstant "Width Animation" (宽度)
    - 555: INTConstant "Height Animation" (高度)
    - 56, 58, 267, 372: LoadImage (图片，原始4个)
    - 376: ImageBatchMulti (批量图片处理，支持动态数量)
    - 410: VHS_VideoCombine (输出视频)
    """
    
    # 验证图片数量
    num_images = len(images)
    if not (4 <= num_images <= 10):
        raise ValueError(f"图片数量必须在 4-10 之间，当前为 {num_images}")
    
    print(f"[INFO] 准备处理 {num_images} 张图片")
    
    # 原始的 LoadImage 节点 ID
    original_image_nodes = [56, 58, 267, 372]
    
    # 如果图片数量超过4张，需要动态添加 LoadImage 节点
    image_node_ids = original_image_nodes.copy()
    
    if num_images > 4:
        # 找到最大的节点 ID
        max_node_id = max(node['id'] for node in workflow['nodes'])
        
        # 创建额外的 LoadImage 节点
        for i in range(4, num_images):
            max_node_id += 1
            new_node_id = max_node_id
            image_node_ids.append(new_node_id)
            
            # 创建新的 LoadImage 节点（复制节点 56 的结构）
            template_node = next(n for n in workflow['nodes'] if n['id'] == 56)
            new_node = {
                "id": new_node_id,
                "type": "LoadImage",
                "pos": [
                    template_node['pos'][0] + (i - 3) * 250,  # 横向排列
                    template_node['pos'][1]
                ],
                "size": template_node['size'].copy(),
                "flags": {},
                "order": template_node['order'] + i - 3,
                "mode": 0,
                "inputs": [
                    {
                        "localized_name": "图像",
                        "name": "image",
                        "type": "COMBO",
                        "widget": {"name": "image"},
                        "link": None
                    },
                    {
                        "localized_name": "选择文件上传",
                        "name": "upload",
                        "type": "IMAGEUPLOAD",
                        "widget": {"name": "upload"},
                        "link": None
                    }
                ],
                "outputs": [
                    {
                        "localized_name": "图像",
                        "name": "IMAGE",
                        "type": "IMAGE",
                        "slot_index": 0,
                        "links": []
                    },
                    {
                        "localized_name": "遮罩",
                        "name": "MASK",
                        "type": "MASK",
                        "links": None
                    }
                ],
                "properties": {
                    "cnr_id": "comfy-core",
                    "ver": "0.3.27",
                    "Node name for S&R": "LoadImage"
                },
                "widgets_values": [images[i], "image"],
                "color": "#432",
                "bgcolor": "#653"
            }
            workflow['nodes'].append(new_node)
            print(f"[CREATE] 创建新的 LoadImage 节点 {new_node_id} 用于图片 {i+1}")
    
    # 查找并更新节点
    for node in workflow['nodes']:
        node_id = node['id']
        node_type = node['type']
        
        # 更新 LoadAudio 节点 (任意ID，根据类型匹配)
        if node_type == 'LoadAudio':
            # 如果 audio_path 是绝对路径，转换为相对于 input 目录的路径
            if os.path.isabs(audio_path):
                # 获取相对于 INPUT_DIR 的路径
                try:
                    from pathlib import Path
                    audio_rel_path = str(Path(audio_path).relative_to(INPUT_DIR))
                except ValueError:
                    # 如果不在 input 目录下，只使用文件名
                    audio_rel_path = os.path.basename(audio_path)
            else:
                # 已经是相对路径，直接使用
                audio_rel_path = audio_path
            
            if isinstance(node.get('widgets_values'), list):
                node['widgets_values'][0] = audio_rel_path
            elif isinstance(node.get('widgets_values'), dict):
                node['widgets_values']['audio'] = audio_rel_path
            print(f"[UPDATE] Node {node_id}: 音频文件设置为 {audio_rel_path}")
        
        # 更新 Number of Frames (552)
        elif node_type == 'INTConstant' and node.get('title') == 'Number of Frames':
            if isinstance(node.get('widgets_values'), list):
                node['widgets_values'][0] = num_frames
            elif isinstance(node.get('widgets_values'), dict):
                node['widgets_values']['value'] = num_frames
            print(f"[UPDATE] Node {node_id}: 帧数设置为 {num_frames}")
        
        # 更新 Frames per second (553)
        elif node_type == 'FloatConstant' and node.get('title') == 'Frames per second':
            if isinstance(node.get('widgets_values'), list):
                node['widgets_values'][0] = fps
            elif isinstance(node.get('widgets_values'), dict):
                node['widgets_values']['value'] = fps
            print(f"[UPDATE] Node {node_id}: FPS设置为 {fps}")
        
        # 更新 Width Animation (554)
        elif node_type == 'INTConstant' and node.get('title') == 'Width Animation':
            if isinstance(node.get('widgets_values'), list):
                node['widgets_values'][0] = width
            elif isinstance(node.get('widgets_values'), dict):
                node['widgets_values']['value'] = width
            print(f"[UPDATE] Node {node_id}: 宽度设置为 {width}")
        
        # 更新 Height Animation (555)
        elif node_type == 'INTConstant' and node.get('title') == 'Height Animation':
            if isinstance(node.get('widgets_values'), list):
                node['widgets_values'][0] = height
            elif isinstance(node.get('widgets_values'), dict):
                node['widgets_values']['value'] = height
            print(f"[UPDATE] Node {node_id}: 高度设置为 {height}")
        
        # 更新所有 LoadImage 节点
        elif node_type == 'LoadImage' and node_id in image_node_ids:
            img_index = image_node_ids.index(node_id)
            if img_index < len(images):
                node['widgets_values'][0] = images[img_index]
                print(f"[UPDATE] Node {node_id}: 图片{img_index+1}设置为 {images[img_index]}")
        
        # 更新 ImageBatchMulti 节点 (376) - 设置输入数量
        elif node_type == 'ImageBatchMulti' and node_id == 376:
            # 更新 inputcount
            if isinstance(node.get('widgets_values'), list):
                node['widgets_values'][0] = num_images
            elif isinstance(node.get('widgets_values'), dict):
                node['widgets_values']['inputcount'] = num_images
            
            # 更新 inputs（确保有足够的输入槽）
            current_inputs = node.get('inputs', [])
            
            # 保留前2个固定输入（image_1, image_2）
            fixed_inputs = current_inputs[:2] if len(current_inputs) >= 2 else current_inputs
            
            # 添加 inputcount 输入（移除连接，使用 widget 值）
            inputcount_input = {
                "name": "inputcount",
                "type": "INT",
                "widget": {"name": "inputcount"},
                "link": None  # 重要：移除连接，使用 widgets_values
            }
            fixed_inputs.append(inputcount_input)
            
            # 创建动态图片输入（从 image_3 到 image_N）
            dynamic_inputs = []
            for i in range(2, num_images):  # 从 image_3 开始
                dynamic_inputs.append({
                    "name": f"image_{i+1}",
                    "type": "IMAGE",
                    "link": None
                })
            
            node['inputs'] = fixed_inputs + dynamic_inputs
            print(f"[UPDATE] Node {node_id}: ImageBatchMulti 输入数量设置为 {num_images}")
        
        # 更新 VHS_VideoCombine 节点 (410) - 设置输出文件名前缀
        elif node_type == 'VHS_VideoCombine' and node_id == 410 and task_id:
            if isinstance(node.get('widgets_values'), dict):
                # 原始前缀格式: "vj/"
                original_prefix = node['widgets_values'].get('filename_prefix', 'vj/')
                # 添加 task_id
                new_prefix = f"vj/{task_id}_"
                node['widgets_values']['filename_prefix'] = new_prefix
                print(f"[UPDATE] Node {node_id}: 输出文件名前缀设置为 {new_prefix}")
    
    # 更新 links - 连接 LoadImage 到 ImageBatchMulti
    # 找到最大的 link ID
    max_link_id = max(link[0] for link in workflow.get('links', [])) if workflow.get('links') else 0
    
    # 删除旧的图片相关连接（899, 900, 903, 904）
    old_image_links = {899, 900, 903, 904}
    workflow['links'] = [link for link in workflow['links'] if link[0] not in old_image_links]
    
    # 创建新的连接
    for i, img_node_id in enumerate(image_node_ids):
        max_link_id += 1
        new_link = [
            max_link_id,           # link_id
            img_node_id,           # source_node_id (LoadImage)
            0,                     # source_slot (IMAGE output)
            376,                   # target_node_id (ImageBatchMulti)
            i,                     # target_slot (image_1=0, image_2=1, image_3=3, ...)
            "IMAGE"                # type
        ]
        workflow['links'].append(new_link)
        
        # 更新 LoadImage 节点的输出 links
        for node in workflow['nodes']:
            if node['id'] == img_node_id:
                if 'outputs' in node and len(node['outputs']) > 0:
                    if node['outputs'][0].get('links') is None:
                        node['outputs'][0]['links'] = []
                    node['outputs'][0]['links'].append(max_link_id)
        
        # 更新 ImageBatchMulti 节点的输入 links
        # 注意：槽位映射为 image_1(0), image_2(1), inputcount(2), image_3(3), image_4(4), ...
        # 所以对于 i >= 2，实际槽位是 i+1
        for node in workflow['nodes']:
            if node['id'] == 376:
                if 'inputs' in node:
                    # 计算实际槽位：前两个图片直接映射，第3个及以后跳过 inputcount
                    actual_slot = i if i < 2 else i + 1
                    if actual_slot < len(node['inputs']):
                        node['inputs'][actual_slot]['link'] = max_link_id
        
        print(f"[LINK] 连接 LoadImage({img_node_id}) -> ImageBatchMulti(376) 槽位 {i}")
    
    return workflow


def submit_workflow_to_comfyui(workflow: dict, client_id: str) -> str:
    """提交 workflow 到 ComfyUI"""
    
    # 转换为 API 格式
    api_workflow = convert_to_api_format(workflow)
    
    # 打印关键节点的 API 格式（调试用）
    print("\n[DEBUG] API 格式的关键节点:")
    for node_id in ['552', '553', '554', '555', '551', '376']:
        if node_id in api_workflow:
            node = api_workflow[node_id]
            print(f"  Node {node_id} ({node['class_type']}): {node['inputs']}")
    
    # 提交请求
    payload = {
        "prompt": api_workflow,
        "client_id": client_id
    }
    
    response = requests.post(f"{COMFYUI_URL}/prompt", json=payload)
    response.raise_for_status()
    
    result = response.json()
    return result.get('prompt_id')


def wait_for_completion(prompt_id: str, task_id: str, timeout: int = None) -> dict:
    """
    等待任务完成
    
    返回:
        {
            "status": "completed" | "failed" | "timeout",
            "output_files": [...],
            "error": "..."
        }
    """
    # 使用配置中的超时，默认 6000 秒
    if timeout is None:
        timeout = CONFIG.get('timeout', {}).get('task_execution', 6000)
    
    start_time = time.time()
    poll_count = 0
    
    while True:
        # 检查超时
        elapsed = time.time() - start_time
        if elapsed > timeout:
            return {
                "status": "timeout",
                "error": f"任务执行超时 ({timeout}秒)"
            }
        
        poll_count += 1
        
        # 查询历史记录
        try:
            response = requests.get(f"{COMFYUI_URL}/history/{prompt_id}")
            response.raise_for_status()
            history = response.json()
            
            if prompt_id in history:
                task_info = history[prompt_id]
                status_info = task_info.get('status', {})
                status_str = status_info.get('status_str', '')
                is_completed = status_info.get('completed', False)
                
                # 每 30 次轮询打印一次调试信息
                if poll_count % 30 == 1:
                    print(f"[DEBUG] 轮询 #{poll_count} | prompt_id={prompt_id}")
                    print(f"[DEBUG]   status_str={status_str}, completed={is_completed}")
                    print(f"[DEBUG]   outputs keys={list(task_info.get('outputs', {}).keys())}")
                
                # 检查是否有错误
                if status_str == 'error':
                    error_msg = str(status_info.get('messages', ''))
                    print(f"[ERROR] ComfyUI 任务失败: {error_msg}")
                    
                    with task_lock:
                        if task_id in tasks:
                            tasks[task_id]['status'] = 'failed'
                            tasks[task_id]['error'] = error_msg
                    
                    persist_task(task_id)
                    
                    return {
                        "status": "failed",
                        "error": error_msg
                    }
                
                # 检查是否完成（通过 outputs 或 status.completed）
                has_outputs = 'outputs' in task_info and task_info['outputs']
                
                if has_outputs or is_completed or status_str == 'success':
                    outputs = task_info.get('outputs', {})
                    output_files = []
                    
                    print(f"[INFO] ComfyUI 任务完成! status_str={status_str}, completed={is_completed}")
                    print(f"[INFO] 输出节点: {list(outputs.keys())}")
                    
                    # 遍历所有输出节点查找视频文件（不局限于节点 410）
                    for node_id, node_output in outputs.items():
                        # 检查 gifs 键（VHS 旧版）
                        videos = node_output.get('gifs', [])
                        # 检查 videos 键（VHS 新版可能用）
                        if not videos:
                            videos = node_output.get('videos', [])
                        # 检查 images 键（某些节点用）
                        if not videos:
                            videos = node_output.get('images', [])
                        
                        for video in videos:
                            if not isinstance(video, dict):
                                continue
                            filename = video.get('filename', '')
                            subfolder = video.get('subfolder', '')
                            
                            # 只匹配视频文件
                            if not filename.lower().endswith(('.mp4', '.webm', '.avi', '.mov', '.gif')):
                                continue
                            
                            video_path = OUTPUT_DIR / subfolder / filename
                            print(f"[INFO] 检查输出文件: {video_path} (存在: {video_path.exists()})")
                            
                            if video_path.exists():
                                output_files.append({
                                    "filename": filename,
                                    "subfolder": subfolder,
                                    "type": video.get('type', 'output'),
                                    "path": str(video_path),
                                    "node_id": node_id
                                })
                    
                    print(f"[INFO] 找到 {len(output_files)} 个视频输出文件")
                    
                    # 更新任务状态
                    with task_lock:
                        if task_id in tasks:
                            tasks[task_id]['status'] = 'completed'
                            tasks[task_id]['output_files'] = output_files
                            tasks[task_id]['completed_at'] = datetime.now().isoformat()
                    
                    persist_task(task_id)
                    
                    return {
                        "status": "completed",
                        "output_files": output_files
                    }
        
        except Exception as e:
            print(f"[WARN] 查询任务状态出错 (轮询 #{poll_count}): {e}")
            import traceback
            traceback.print_exc()
        
        # 更新进度
        with task_lock:
            if task_id in tasks:
                tasks[task_id]['elapsed_seconds'] = int(elapsed)
        
        # 等待后重试
        time.sleep(2)


def process_task_async(task_id: str, workflow: dict, client_id: str):
    """异步处理任务"""
    try:
        # 提交到 ComfyUI
        prompt_id = submit_workflow_to_comfyui(workflow, client_id)
        
        with task_lock:
            if task_id in tasks:
                tasks[task_id]['prompt_id'] = prompt_id
                tasks[task_id]['status'] = 'processing'
        
        # 持久化（保存 prompt_id）
        persist_task(task_id)
        
        # 等待完成
        result = wait_for_completion(prompt_id, task_id)
        
        # 打印任务完成信息
        print("\n" + "=" * 60)
        print(f"✅ 任务完成: {task_id}")
        print("=" * 60)
        print(f"状态: {result['status']}")
        
        if result['status'] == 'completed':
            print(f"\n📹 输出文件:")
            if result.get('output_files'):
                for idx, file_info in enumerate(result['output_files'], 1):
                    print(f"  {idx}. {file_info['filename']}")
                    print(f"     路径: {file_info['path']}")
                    print(f"     子目录: {file_info.get('subfolder', 'N/A')}")
                    print(f"     大小: {os.path.getsize(file_info['path']) / 1024 / 1024:.2f} MB")
            else:
                print("  无输出文件")
        elif result['status'] == 'failed':
            print(f"\n❌ 错误信息: {result.get('error', 'Unknown error')}")
        elif result['status'] == 'timeout':
            print(f"\n⏱️  任务超时")
        
        # 获取任务详情
        with task_lock:
            if task_id in tasks:
                task = tasks[task_id]
                print(f"\n⏱️  耗时: {task.get('elapsed_seconds', 0)} 秒")
                print(f"📋 参数:")
                print(f"   帧数: {task['params'].get('num_frames', 'N/A')}")
                print(f"   分辨率: {task['params'].get('width', 'N/A')}x{task['params'].get('height', 'N/A')}")
                print(f"   帧率: {task['params'].get('fps', 'N/A')} fps")
                print(f"   音频: {os.path.basename(task['params'].get('audio_path', 'N/A'))}")
                print(f"   图片数: {len(task['params'].get('images', []))}")
        
        print("=" * 60 + "\n")
    
    except Exception as e:
        print(f"任务 {task_id} 失败: {e}")
        with task_lock:
            if task_id in tasks:
                tasks[task_id]['status'] = 'failed'
                tasks[task_id]['error'] = str(e)
        
        # 持久化
        persist_task(task_id)


# =============================================================================
# API 端点
# =============================================================================

@app.route('/')
def home():
    """主页"""
    return jsonify({
        "service": "VJ 视频生成 API",
        "version": "1.0.0",
        "endpoints": {
            "upload_image": "POST /api/upload-image",
            "upload_audio": "POST /api/upload-audio",
            "generate": "POST /api/generate-video",
            "status": "GET /api/tasks/{task_id}",
            "download": "GET /api/tasks/{task_id}/download",
            "list": "GET /api/tasks",
            "health": "GET /health"
        }
    })


@app.route('/health')
def health():
    """健康检查"""
    try:
        # 检查 ComfyUI 是否可用
        response = requests.get(f"{COMFYUI_URL}/system_stats", timeout=3)
        comfyui_status = "running" if response.status_code == 200 else "unavailable"
    except:
        comfyui_status = "unavailable"
    
    return jsonify({
        "status": "healthy",
        "comfyui": comfyui_status,
        "tasks_count": len(tasks)
    })


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除可能导致问题的字符
    
    - 移除或替换空格
    - 保留基本的字母、数字、下划线、连字符
    - 保留文件扩展名
    """
    import re
    from pathlib import Path
    
    # 分离文件名和扩展名
    name = Path(filename).stem
    ext = Path(filename).suffix
    
    # 替换空格为下划线
    name = name.replace(' ', '_')
    
    # 移除特殊字符，只保留字母、数字、下划线、连字符
    name = re.sub(r'[^\w\-]', '', name)
    
    # 如果文件名为空，使用时间戳
    if not name:
        import time
        name = f"file_{int(time.time())}"
    
    return f"{name}{ext}"


@app.route('/api/upload-image', methods=['POST'])
def upload_image():
    """
    上传图片到 ComfyUI 的 input 目录
    
    文件将保存到: /Users/coco/coco-code/ComfyUI/input/
    
    请求方式1 - multipart/form-data（推荐）:
        POST /api/upload-image
        Content-Type: multipart/form-data
        
        file: <图片文件>
        filename: "my_image.jpg"  // 可选，不提供则使用原文件名
    
    请求方式2 - JSON base64:
        POST /api/upload-image
        Content-Type: application/json
        
        {
            "filename": "my_image.jpg",
            "data": "base64_encoded_image_data"
        }
    
    响应:
    {
        "success": true,
        "filename": "my_image.jpg",
        "path": "/Users/coco/coco-code/ComfyUI/input/my_image.jpg",
        "size": 1024000,
        "message": "图片上传成功"
    }
    
    注意：上传后可以在生成视频时直接使用文件名，例如：
    {
        "images": ["my_image.jpg"]
    }
    """
    try:
        # 方式1: multipart/form-data
        if 'file' in request.files:
            file = request.files['file']
            
            if file.filename == '':
                return jsonify({
                    "success": False,
                    "error": "没有选择文件"
                }), 400
            
            # 获取文件名和 task_id
            original_filename = request.form.get('filename', file.filename)
            task_id = request.form.get('task_id', str(uuid.uuid4()))
            
            # 清理文件名
            filename = sanitize_filename(original_filename)
            
            # 如果文件名被修改了，记录日志
            if filename != original_filename:
                print(f"[INFO] 图片文件名已清理: '{original_filename}' -> '{filename}'")
            
            # 验证文件扩展名
            allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
            file_ext = os.path.splitext(filename)[1].lower()
            
            if file_ext not in allowed_extensions:
                return jsonify({
                    "success": False,
                    "error": f"不支持的图片格式: {file_ext}，支持的格式: {', '.join(allowed_extensions)}"
                }), 400
            
            # 创建任务目录
            task_dir = INPUT_DIR / task_id
            task_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存文件
            file_path = task_dir / filename
            file.save(file_path)
            
            file_size = os.path.getsize(file_path)
            relative_path = f"{task_id}/{filename}"
            
            return jsonify({
                "success": True,
                "task_id": task_id,
                "filename": filename,
                "relative_path": relative_path,
                "path": str(file_path),
                "size": file_size,
                "message": "图片上传成功"
            }), 201
        
        # 方式2: JSON base64
        elif request.is_json:
            data = request.get_json()
            
            if 'filename' not in data or 'data' not in data:
                return jsonify({
                    "success": False,
                    "error": "缺少必填参数: filename 和 data"
                }), 400
            
            original_filename = data['filename']
            image_data = data['data']
            task_id = data.get('task_id', str(uuid.uuid4()))
            
            # 清理文件名
            filename = sanitize_filename(original_filename)
            
            # 如果文件名被修改了，记录日志
            if filename != original_filename:
                print(f"[INFO] 图片文件名已清理: '{original_filename}' -> '{filename}'")
            
            # 验证文件扩展名
            allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
            file_ext = os.path.splitext(filename)[1].lower()
            
            if file_ext not in allowed_extensions:
                return jsonify({
                    "success": False,
                    "error": f"不支持的图片格式: {file_ext}"
                }), 400
            
            # 解码 base64
            import base64
            try:
                image_bytes = base64.b64decode(image_data)
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": f"Base64 解码失败: {str(e)}"
                }), 400
            
            # 创建任务目录
            task_dir = INPUT_DIR / task_id
            task_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存文件
            file_path = task_dir / filename
            with open(file_path, 'wb') as f:
                f.write(image_bytes)
            
            file_size = len(image_bytes)
            relative_path = f"{task_id}/{filename}"
            
            return jsonify({
                "success": True,
                "task_id": task_id,
                "filename": filename,
                "relative_path": relative_path,
                "path": str(file_path),
                "size": file_size,
                "message": "图片上传成功"
            }), 201
        
        else:
            return jsonify({
                "success": False,
                "error": "请使用 multipart/form-data 或 JSON 格式上传"
            }), 400
    
    except Exception as e:
        print(f"上传图片出错: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/upload-audio', methods=['POST'])
def upload_audio():
    """
    上传音频文件到 ComfyUI 的 input 目录
    
    文件将保存到: /Users/coco/coco-code/ComfyUI/input/
    
    请求方式1 - multipart/form-data（推荐）:
        POST /api/upload-audio
        Content-Type: multipart/form-data
        
        file: <音频文件>
        filename: "my_audio.mp3"  // 可选
    
    请求方式2 - JSON base64:
        POST /api/upload-audio
        Content-Type: application/json
        
        {
            "filename": "my_audio.mp3",
            "data": "base64_encoded_audio_data"
        }
    
    响应:
    {
        "success": true,
        "filename": "my_audio.mp3",
        "path": "/Users/coco/coco-code/ComfyUI/input/my_audio.mp3",
        "size": 2048000,
        "message": "音频上传成功"
    }
    
    注意：上传后可以在生成视频时直接使用文件名，例如：
    {
        "audio_path": "my_audio.mp3"
    }
    """
    try:
        # 方式1: multipart/form-data
        if 'file' in request.files:
            file = request.files['file']
            
            if file.filename == '':
                return jsonify({
                    "success": False,
                    "error": "没有选择文件"
                }), 400
            
            # 获取文件名和 task_id
            original_filename = request.form.get('filename', file.filename)
            task_id = request.form.get('task_id', str(uuid.uuid4()))
            
            # 清理文件名
            filename = sanitize_filename(original_filename)
            
            # 如果文件名被修改了，记录日志
            if filename != original_filename:
                print(f"[INFO] 音频文件名已清理: '{original_filename}' -> '{filename}'")
            
            # 验证文件扩展名
            allowed_extensions = {'.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac'}
            file_ext = os.path.splitext(filename)[1].lower()
            
            if file_ext not in allowed_extensions:
                return jsonify({
                    "success": False,
                    "error": f"不支持的音频格式: {file_ext}，支持的格式: {', '.join(allowed_extensions)}"
                }), 400
            
            # 创建任务目录
            task_dir = INPUT_DIR / task_id
            task_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存文件
            file_path = task_dir / filename
            file.save(file_path)
            
            file_size = os.path.getsize(file_path)
            relative_path = f"{task_id}/{filename}"
            
            return jsonify({
                "success": True,
                "task_id": task_id,
                "filename": filename,
                "relative_path": relative_path,
                "path": str(file_path),
                "size": file_size,
                "message": "音频上传成功"
            }), 201
        
        # 方式2: JSON base64
        elif request.is_json:
            data = request.get_json()
            
            if 'filename' not in data or 'data' not in data:
                return jsonify({
                    "success": False,
                    "error": "缺少必填参数: filename 和 data"
                }), 400
            
            original_filename = data['filename']
            audio_data = data['data']
            task_id = data.get('task_id', str(uuid.uuid4()))
            
            # 清理文件名
            filename = sanitize_filename(original_filename)
            
            # 如果文件名被修改了，记录日志
            if filename != original_filename:
                print(f"[INFO] 音频文件名已清理: '{original_filename}' -> '{filename}'")
            
            # 验证文件扩展名
            allowed_extensions = {'.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac'}
            file_ext = os.path.splitext(filename)[1].lower()
            
            if file_ext not in allowed_extensions:
                return jsonify({
                    "success": False,
                    "error": f"不支持的音频格式: {file_ext}"
                }), 400
            
            # 解码 base64
            import base64
            try:
                audio_bytes = base64.b64decode(audio_data)
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": f"Base64 解码失败: {str(e)}"
                }), 400
            
            # 创建任务目录
            task_dir = INPUT_DIR / task_id
            task_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存文件
            file_path = task_dir / filename
            with open(file_path, 'wb') as f:
                f.write(audio_bytes)
            
            file_size = len(audio_bytes)
            relative_path = f"{task_id}/{filename}"
            
            return jsonify({
                "success": True,
                "task_id": task_id,
                "filename": filename,
                "relative_path": relative_path,
                "path": str(file_path),
                "size": file_size,
                "message": "音频上传成功"
            }), 201
            
            return jsonify({
                "success": True,
                "filename": filename,
                "path": str(file_path),
                "size": file_size,
                "message": "音频上传成功"
            }), 201
        
        else:
            return jsonify({
                "success": False,
                "error": "请使用 multipart/form-data 或 JSON 格式上传"
            }), 400
    
    except Exception as e:
        print(f"上传音频出错: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/generate-video', methods=['POST'])
def generate_video():
    """
    生成音频反应式视频
    
    请求体:
    {
        "audio_path": "/path/to/audio.mp3",  // 必填：音频文件路径（绝对路径或相对于 input/ 的路径）
        "num_frames": 960,                    // 可选：总帧数，范围 1-2000，默认 50
        "width": 512,                         // 可选：视频宽度，范围 64-2048，默认 384
        "height": 512,                        // 可选：视频高度，范围 64-2048，默认 384
        "fps": 16,                            // 可选：帧率，范围 8-60，默认 16
        "images": [                           // 必填：图片文件名列表（相对于 input/ task_id/），数量 4-10 张
            "task_id/image1.jpg",
            "task_id/image2.jpg",
            "task_id/image3.jpg",
            "task_id/image4.jpg",
            // ... 最多 10 张
        ]
    }
    
    响应:
    {
        "success": true,
        "task_id": "abc-123-def",
        "status": "queued",
        "message": "任务已提交，正在处理中"
    }
    
    注意：
    - 图片数量必须在 4-10 张之间
    - 参数限制可在 config.json 中配置
    - 输出视频文件名会自动包含 task_id 前缀
    """
    try:
        data = request.get_json()
        
        # 验证必填参数
        if not data or 'audio_path' not in data:
            return jsonify({
                "success": False,
                "error": "缺少必填参数: audio_path"
            }), 400
        
        if 'images' not in data or not isinstance(data['images'], list):
            return jsonify({
                "success": False,
                "error": "缺少必填参数: images (必须是数组，包含 4-10 张图片)"
            }), 400
        
        audio_path = data['audio_path']
        images = data['images']
        
        # 验证图片数量
        if not (4 <= len(images) <= 10):
            return jsonify({
                "success": False,
                "error": f"图片数量必须在 4-10 之间，当前提供了 {len(images)} 张"
            }), 400
        
        # 处理音频路径
        if not os.path.isabs(audio_path):
            # 相对路径，转换为绝对路径
            audio_path = str(INPUT_DIR / audio_path)
        
        # 验证音频文件存在
        if not os.path.exists(audio_path):
            return jsonify({
                "success": False,
                "error": f"音频文件不存在: {audio_path}"
            }), 400
        
        # 获取参数（带默认值）
        num_frames = data.get('num_frames', 50)
        width = data.get('width', 384)
        height = data.get('height', 384)
        fps = data.get('fps', 16)
        
        # 参数验证（使用配置文件中的限制）
        if not (NUM_FRAMES_MIN <= num_frames <= NUM_FRAMES_MAX):
            return jsonify({
                "success": False,
                "error": f"num_frames 必须在 {NUM_FRAMES_MIN}-{NUM_FRAMES_MAX} 之间"
            }), 400
        
        # 宽度验证（支持选项列表或范围）
        if WIDTH_OPTIONS is not None:
            if width not in WIDTH_OPTIONS:
                return jsonify({
                    "success": False,
                    "error": f"width 必须是 {'/'.join(map(str, WIDTH_OPTIONS))} 之一"
                }), 400
        else:
            if not (WIDTH_MIN <= width <= WIDTH_MAX):
                return jsonify({
                    "success": False,
                    "error": f"width 必须在 {WIDTH_MIN}-{WIDTH_MAX} 之间"
                }), 400
        
        # 高度验证（支持选项列表或范围）
        if HEIGHT_OPTIONS is not None:
            if height not in HEIGHT_OPTIONS:
                return jsonify({
                    "success": False,
                    "error": f"height 必须是 {'/'.join(map(str, HEIGHT_OPTIONS))} 之一"
                }), 400
        else:
            if not (HEIGHT_MIN <= height <= HEIGHT_MAX):
                return jsonify({
                    "success": False,
                    "error": f"height 必须在 {HEIGHT_MIN}-{HEIGHT_MAX} 之间"
                }), 400
        
        if not (FPS_MIN <= fps <= FPS_MAX):
            return jsonify({
                "success": False,
                "error": f"fps 必须在 {FPS_MIN}-{FPS_MAX} 之间"
            }), 400
        
        # 验证图片文件
        for img in images:
            img_path = INPUT_DIR / img
            if not img_path.exists():
                return jsonify({
                    "success": False,
                    "error": f"图片文件不存在: {img}"
                }), 400
        
        # 打印完整的请求参数（验证通过后）
        print(f"\n{'='*60}")
        print(f"📋 生成视频参数:")
        print(f"{'='*60}")
        print(f"   音频文件: {audio_path}")
        print(f"   帧数: {num_frames}")
        print(f"   分辨率: {width}x{height}")
        print(f"   帧率: {fps} fps")
        print(f"   图片列表 ({len(images)} 张):")
        for i, img in enumerate(images, 1):
            print(f"      {i}. {img}")
        print(f"{'='*60}\n")
        
        # 加载 workflow 模板
        workflow = load_workflow_template()
        
        # 生成任务 ID（在更新参数前生成，以便在输出文件名中使用）
        task_id = str(uuid.uuid4())
        client_id = str(uuid.uuid4())
        
        # 更新参数（传入 task_id 用于设置输出文件名）
        workflow = update_workflow_params(
            workflow, audio_path, num_frames, width, height, fps, images, task_id
        )
        
        # 创建任务记录
        with task_lock:
            tasks[task_id] = {
                "task_id": task_id,
                "status": "queued",
                "params": {
                    "audio_path": audio_path,
                    "num_frames": num_frames,
                    "width": width,
                    "height": height,
                    "fps": fps,
                    "images": images
                },
                "created_at": datetime.now().isoformat(),
                "client_id": client_id,
                "prompt_id": None,
                "output_files": [],
                "error": None,
                "elapsed_seconds": 0
            }
        
        # 持久化任务
        persist_task(task_id)
        
        # 异步处理任务
        thread = threading.Thread(
            target=process_task_async,
            args=(task_id, workflow, client_id),
            daemon=True
        )
        thread.start()
        
        return jsonify({
            "success": True,
            "task_id": task_id,
            "status": "queued",
            "message": "任务已提交，正在处理中",
            "check_status_url": f"/api/tasks/{task_id}"
        }), 202
    
    except Exception as e:
        print(f"生成视频出错: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task_status(task_id: str):
    """
    查询任务状态
    
    响应:
    {
        "success": true,
        "task": {
            "task_id": "abc-123",
            "status": "queued" | "processing" | "completed" | "failed",
            "params": {...},
            "created_at": "2026-02-04T10:00:00",
            "completed_at": "2026-02-04T10:05:30",
            "elapsed_seconds": 330,
            "output_files": [...],
            "video_path": "/absolute/path/to/video.mp4"  # 仅在 status='completed' 时返回
        }
    }
    """
    with task_lock:
        if task_id not in tasks:
            return jsonify({
                "success": False,
                "error": "任务不存在"
            }), 404
        
        task = tasks[task_id].copy()
    
    # 如果任务完成且有输出文件，添加 video_path 字段
    if task['status'] == 'completed' and task.get('output_files'):
        # 默认返回第一个视频文件的绝对路径
        task['video_path'] = task['output_files'][0]['path']
        
        # 如果有多个视频，也提供一个列表
        if len(task['output_files']) > 1:
            task['video_paths'] = [f['path'] for f in task['output_files']]
    
    # 打印任务详情（用于调试）
    print(f"\n[DEBUG] 返回任务状态:")
    print(f"  任务ID: {task_id}")
    print(f"  状态: {task['status']}")
    print(f"  参数: {json.dumps(task.get('params', {}), ensure_ascii=False)}")
    if task['status'] == 'completed':
        print(f"  输出文件: {len(task.get('output_files', []))} 个")
        if task.get('video_path'):
            print(f"  视频路径: {task['video_path']}")
    
    return jsonify({
        "success": True,
        "task": task
    })


@app.route('/api/tasks', methods=['GET'])
def list_tasks():
    """
    列出所有任务
    
    参数:
        limit: 返回数量限制，默认 50
        status: 筛选状态 (queued/processing/completed/failed)
    """
    limit = request.args.get('limit', 50, type=int)
    status_filter = request.args.get('status')
    
    with task_lock:
        task_list = list(tasks.values())
    
    # 筛选
    if status_filter:
        task_list = [t for t in task_list if t['status'] == status_filter]
    
    # 排序（最新的在前）
    task_list.sort(key=lambda x: x['created_at'], reverse=True)
    
    # 限制数量
    task_list = task_list[:limit]
    
    return jsonify({
        "success": True,
        "tasks": task_list,
        "total": len(task_list)
    })


@app.route('/api/tasks/<task_id>/download', methods=['GET'])
def download_video(task_id: str):
    """
    下载生成的视频
    
    参数:
        index: 文件索引，默认 0（第一个文件）
    """
    with task_lock:
        if task_id not in tasks:
            return jsonify({
                "success": False,
                "error": "任务不存在"
            }), 404
        
        task = tasks[task_id]
    
    if task['status'] != 'completed':
        return jsonify({
            "success": False,
            "error": f"任务未完成，当前状态: {task['status']}"
        }), 400
    
    if not task['output_files']:
        return jsonify({
            "success": False,
            "error": "没有找到输出文件"
        }), 404
    
    # 获取文件索引
    file_index = request.args.get('index', 0, type=int)
    
    if file_index >= len(task['output_files']):
        return jsonify({
            "success": False,
            "error": f"文件索引超出范围，共有 {len(task['output_files'])} 个文件"
        }), 400
    
    file_info = task['output_files'][file_index]
    file_path = file_info['path']
    
    if not os.path.exists(file_path):
        return jsonify({
            "success": False,
            "error": "文件不存在"
        }), 404
    
    return send_file(
        file_path,
        mimetype='video/mp4',
        as_attachment=True,
        download_name=file_info['filename']
    )


@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def cancel_task(task_id: str):
    """
    取消任务（如果任务还在队列中）
    """
    with task_lock:
        if task_id not in tasks:
            return jsonify({
                "success": False,
                "error": "任务不存在"
            }), 404
        
        task = tasks[task_id]
        
        if task['status'] in ['completed', 'failed']:
            return jsonify({
                "success": False,
                "error": f"任务已{task['status']}，无法取消"
            }), 400
        
        # 尝试中断 ComfyUI 的执行
        if task.get('prompt_id'):
            try:
                requests.post(f"{COMFYUI_URL}/interrupt")
            except:
                pass
        
        # 标记为已取消
        task['status'] = 'cancelled'
        task['cancelled_at'] = datetime.now().isoformat()
    
    return jsonify({
        "success": True,
        "message": "任务已取消"
    })


# =============================================================================
# 主程序
# =============================================================================

if __name__ == '__main__':
    # 设置 Windows 控制台编码为 UTF-8
    import sys
    import io
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    print("=" * 60)
    print("🎬 VJ 视频生成 API 服务")
    print("=" * 60)
    print(f"ComfyUI URL: {COMFYUI_URL}")
    print(f"Workflow 模板: {WORKFLOW_TEMPLATE}")
    print(f"输入目录: {INPUT_DIR}")
    print(f"输出目录: {OUTPUT_DIR}")
    print(f"任务存储: {TASK_STORAGE_FILE}")
    
    # 恢复之前的任务
    restore_tasks_from_disk()
    
    print("=" * 60)
    print("📋 可用的 API 端点:")
    print()
    print("  视频生成:")
    print("    POST   /api/generate-video      生成视频")
    print()
    print("  任务管理:")
    print("    GET    /api/tasks/{task_id}     查询任务状态")
    print("    GET    /api/tasks               列出所有任务")
    print("    DELETE /api/tasks/{task_id}     取消任务")
    print()
    print("  文件上传:")
    print("    POST   /api/upload-image        上传图片")
    print("    POST   /api/upload-audio        上传音频")
    print()
    print("  下载:")
    print("    GET    /api/tasks/{task_id}/download  下载视频")
    print()
    print("  其他:")
    print("    GET    /health                  健康检查")
    print()
    print("=" * 60)
    print(f"🚀 启动服务: http://localhost:5002")
    print("=" * 60)
    print()
    
    app.run(host='0.0.0.0', port=5002, debug=True, threaded=True)
