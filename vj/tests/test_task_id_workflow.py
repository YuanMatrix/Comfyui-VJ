#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试基于 task_id 的文件上传和视频生成工作流

新的工作流:
1. 先上传文件（音频/图片）到 input/task_id/ 目录
2. 使用相对路径 "task_id/filename" 生成视频
3. 输出视频文件名会包含 task_id 前缀

优化:
- 使用并发上传多个图片，提高上传效率
- 使用 upload_utils 工具模块
"""

import requests
import json
import time
import sys
import io
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# 设置 Windows 控制台编码为 UTF-8
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加父目录到路径，以便导入 upload_utils
sys.path.insert(0, str(Path(__file__).parent.parent))
from upload_utils import BatchUploader

# API 基础 URL
BASE_URL = "http://localhost:5002/api"


def print_section(title):
    """打印分隔线"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def test_task_id_workflow():
    """测试完整的 task_id 工作流"""

    # 使用一个统一的 task_id
    task_id = "test-task-123"

    # 初始化批量上传器
    uploader = BatchUploader(base_url=BASE_URL, max_workers=4)

    print_section("步骤 1: 上传音频文件（指定 task_id）")

    # 使用相对路径，从 ComfyUI 根目录开始
    comfyui_root = Path(__file__).parent.parent.parent
    audio_file = comfyui_root / "input" / "demo3.mp3"

    if not audio_file.exists():
        print(f"❌ 测试音频文件不存在: {audio_file}")
        return

    # 上传音频
    audio_result = uploader.upload_file(str(audio_file), task_id, file_type="audio")

    if audio_result["success"]:
        print(f"✅ 音频上传成功")
        print(f"   Task ID: {task_id}")
        print(f"   相对路径: {audio_result['relative_path']}")
        print(f"   完整路径: {audio_result['full_path']}")
        audio_relative_path = audio_result["relative_path"]
    else:
        print(f"❌ 音频上传失败: {audio_result['error']}")
        return

    print_section("步骤 2: 并发上传多个图片（使用相同的 task_id）")

    # 使用相对路径
    image_files = [
        str(comfyui_root / "input" / "11.jpg"),
        str(comfyui_root / "input" / "12.jpg"),
        str(comfyui_root / "input" / "13.jpg"),
        str(comfyui_root / "input" / "14.jpg"),
    ]

    # 使用批量上传
    upload_result = uploader.batch_upload(
        image_files, task_id, file_type="image", show_progress=True
    )

    # 获取上传成功的图片相对路径
    uploaded_images = [item["relative_path"] for item in upload_result["uploaded"]]

    if len(uploaded_images) < 4:
        print(f"\n⚠️ 只上传了 {len(uploaded_images)}/4 张图片，继续使用默认图片")
        uploaded_images = uploaded_images + ["11.jpg"] * (4 - len(uploaded_images))

    print_section("步骤 3: 生成视频（使用上传的文件）")

    # 提交视频生成任务
    generate_data = {
        "audio_path": audio_relative_path,  # 使用相对路径
        "num_frames": 960,
        "width": 200,
        "height": 200,
        "fps": 16,
        "images": uploaded_images,  # 使用上传的图片相对路径
    }

    print(f"请求参数:")
    print(json.dumps(generate_data, indent=2, ensure_ascii=False))

    response = requests.post(f"{BASE_URL}/generate-video", json=generate_data)

    if response.status_code != 202:
        print(f"❌ 视频生成请求失败: {response.text}")
        return

    result = response.json()
    generation_task_id = result["task_id"]

    print(f"✅ 任务已提交")
    print(f"   Generation Task ID: {generation_task_id}")
    print(f"   Status URL: {result['check_status_url']}")

    print_section("步骤 4: 轮询任务状态")

    max_wait_seconds = 300  # 最多等待 5 分钟
    start_time = time.time()

    while (time.time() - start_time) < max_wait_seconds:
        try:
            response = requests.get(f"{BASE_URL}/tasks/{generation_task_id}")

            if response.status_code != 200:
                print(f"❌ 查询状态失败 (HTTP {response.status_code})")
                print(f"   响应: {response.text}")
                break

            result = response.json()

            # API 返回格式: {"success": true, "task": {...}}
            if not result.get("success"):
                print(f"❌ API 返回错误: {result.get('error', 'Unknown error')}")
                break

            task_status = result.get("task", {})
            status = task_status.get("status")

            if not status:
                print(f"⚠️ 响应中缺少 'status' 字段")
                print(
                    f"   返回的数据: {json.dumps(result, indent=2, ensure_ascii=False)}"
                )
                break

        except requests.exceptions.RequestException as e:
            print(f"❌ 网络请求失败: {e}")
            break
        except json.JSONDecodeError as e:
            print(f"❌ JSON 解析失败: {e}")
            print(f"   响应内容: {response.text[:200]}")
            break
        except Exception as e:
            print(f"❌ 未知错误: {e}")
            import traceback

            traceback.print_exc()
            break

        if status == "completed":
            print(f"\n✅ 视频生成完成！")

            # 输出视频文件（可能是字典列表或字符串列表）
            output_files = task_status.get("output_files", [])
            if output_files:
                print(f"   输出文件:")
                for item in output_files:
                    if isinstance(item, dict):
                        video_path = item.get("path", item.get("filename", str(item)))
                    else:
                        video_path = str(item)
                    print(f"      {video_path}")

            # 如果有 video_path 字段（新的 API 格式）
            if "video_path" in task_status:
                print(f"   视频路径: {task_status['video_path']}")

            print(f"   耗时: {task_status.get('elapsed_seconds', 0):.1f} 秒")

            # 检查文件名是否包含 task_id
            all_paths = []
            for item in output_files:
                if isinstance(item, dict):
                    all_paths.append(item.get("path", ""))
                else:
                    all_paths.append(str(item))

            if "video_path" in task_status:
                all_paths.append(task_status["video_path"])

            has_task_prefix = any(
                generation_task_id in path for path in all_paths if path
            )

            if has_task_prefix:
                print(f"\n✅ 输出文件名包含 task_id 前缀！")
            else:
                print(f"\n⚠️ 输出文件名没有 task_id 前缀")

            break

        elif status == "failed":
            print(f"\n❌ 视频生成失败")
            print(f"   错误: {task_status.get('error', 'Unknown error')}")
            break

        else:
            elapsed = time.time() - start_time
            print(f"⏳ 状态: {status} (已等待 {elapsed:.1f}s)", end="\r")
            time.sleep(3)
    else:
        print(f"\n⏰ 等待超时 ({max_wait_seconds}s)")

    print_section("测试完成")

    print(f"\n📁 检查文件目录:")
    print(f"   输入目录: {comfyui_root / 'input' / task_id}")
    print(f"   输出目录: {comfyui_root / 'output'}")
    print(f"\n   输入文件应该在 input/{task_id}/ 下")
    print(f"   输出视频名称应该包含 {generation_task_id}")


if __name__ == "__main__":
    try:
        test_task_id_workflow()
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被中断")
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback

        traceback.print_exc()
