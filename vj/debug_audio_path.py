#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试音频路径传递问题
"""
import os
from pathlib import Path

# 模拟 INPUT_DIR
INPUT_DIR = Path(r"C:\Users\admin\Downloads\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable\ComfyUI\input")

# 你的 task 目录
task_id = "task_1770545279069_cc9h1cbmi"
audio_filename = "声纹千年.mp3"

# 方式1：使用相对路径（API 调用时）
audio_path_relative = f"{task_id}/{audio_filename}"
print(f"相对路径: {audio_path_relative}")

# 方式2：转换为绝对路径（API 内部处理）
audio_path_absolute = str(INPUT_DIR / audio_path_relative)
print(f"绝对路径: {audio_path_absolute}")

# 方式3：检查文件是否存在
file_exists = os.path.exists(audio_path_absolute)
print(f"文件存在: {file_exists}")

# 方式4：转换回相对路径（update_workflow_params 中）
try:
    audio_rel_path = str(Path(audio_path_absolute).relative_to(INPUT_DIR))
    print(f"转换回相对路径: {audio_rel_path}")
except ValueError as e:
    print(f"转换失败: {e}")
    audio_rel_path = os.path.basename(audio_path_absolute)
    print(f"只使用文件名: {audio_rel_path}")

# 方式5：检查 ComfyUI 能否找到这个文件
comfyui_audio_path = INPUT_DIR / audio_rel_path
print(f"ComfyUI 应该查找: {comfyui_audio_path}")
print(f"ComfyUI 能否找到: {comfyui_audio_path.exists()}")
