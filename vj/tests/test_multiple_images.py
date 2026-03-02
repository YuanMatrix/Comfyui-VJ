#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试多图片视频生成 (4-10 张图片)

演示如何使用 API 生成包含不同数量图片的视频
"""

import requests
import time
import json
import uuid
from pathlib import Path
from typing import List
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))
from vj.upload_utils import BatchUploader

# API 配置
API_BASE_URL = "http://localhost:5002/api"

# 测试文件路径
TEST_IMAGES_DIR = Path(__file__).parent.parent.parent / "input" / "test_images"
TEST_AUDIO = Path(__file__).parent.parent.parent / "input" / "demo1.flac"


def test_video_with_n_images(num_images: int = 6, image_paths: List[str] = None):
    """
    测试使用 N 张图片生成视频

    Args:
        num_images: 图片数量 (4-10)
        image_paths: 图片路径列表，如果为 None 则使用默认图片
    """
    print(f"\n{'=' * 60}")
    print(f"🎬 测试 {num_images} 张图片的视频生成")
    print(f"{'=' * 60}\n")

    # 生成唯一的 task_id
    task_id = str(uuid.uuid4())
    print(f"📋 任务 ID: {task_id}\n")

    # 1. 上传图片
    print(f"📤 步骤 1: 并发上传 {num_images} 张图片...")

    if image_paths is None:
        # 使用默认测试图片
        image_paths = [TEST_IMAGES_DIR / f"image{i + 1}.jpg" for i in range(num_images)]

    # 验证图片文件存在
    for img_path in image_paths:
        if not Path(img_path).exists():
            print(f"❌ 错误: 图片文件不存在: {img_path}")
            print(f"   请先准备测试图片")
            return

    uploader = BatchUploader(base_url=API_BASE_URL)

    try:
        results = uploader.batch_upload(
            file_paths=[str(p) for p in image_paths],
            task_id=task_id,
            file_type="image",
            show_progress=True,
        )

        if not results["success"]:
            print(f"\n❌ 图片上传失败:")
            for error in results["failed"]:
                print(f"   - {error['filename']}: {error['error']}")
            return

        print(f"\n✅ {results['success_count']} 张图片上传成功\n")

        # 获取图片的相对路径（用于 API 请求）
        uploaded_images = [img["relative_path"] for img in results["uploaded"]]

    except Exception as e:
        print(f"❌ 上传过程出错: {e}")
        return

    # 2. 上传音频
    print("📤 步骤 2: 上传音频文件...")

    if not TEST_AUDIO.exists():
        print(f"❌ 错误: 音频文件不存在: {TEST_AUDIO}")
        return

    try:
        audio_results = uploader.upload_file(
            file_path=str(TEST_AUDIO), task_id=task_id, file_type="audio"
        )

        if not audio_results["success"]:
            print(f"❌ 音频上传失败: {audio_results.get('error', 'Unknown error')}")
            return

        audio_relative_path = audio_results["relative_path"]
        print(f"✅ 音频上传成功: {audio_relative_path}\n")

    except Exception as e:
        print(f"❌ 音频上传出错: {e}")
        return

    # 3. 生成视频
    print("🎥 步骤 3: 提交视频生成任务...")

    # 构建请求参数
    request_data = {
        "audio_path": audio_relative_path,
        "images": uploaded_images,
        "num_frames": 480,  # 较少的帧数用于快速测试
        "width": 200,
        "height": 200,
        "fps": 16,
    }

    print(f"📋 请求参数:")
    print(f"   - 音频: {request_data['audio_path']}")
    print(f"   - 图片数量: {len(request_data['images'])}")
    print(f"   - 帧数: {request_data['num_frames']}")
    print(f"   - 分辨率: {request_data['width']}x{request_data['height']}")
    print(f"   - 帧率: {request_data['fps']} fps")
    print()

    try:
        response = requests.post(
            f"{API_BASE_URL}/generate-video", json=request_data, timeout=10
        )

        if response.status_code != 202:
            print(f"❌ 视频生成请求失败: {response.status_code}")
            print(f"   错误信息: {response.text}")
            return

        result = response.json()
        video_task_id = result["task_id"]

        print(f"✅ 视频生成任务已提交")
        print(f"   任务 ID: {video_task_id}\n")

    except requests.RequestException as e:
        print(f"❌ 请求失败: {e}")
        return

    # 4. 轮询任务状态
    print("⏳ 步骤 4: 等待视频生成完成...")

    max_wait_time = 600  # 10 分钟超时
    poll_interval = 3  # 每 3 秒查询一次
    start_time = time.time()

    while True:
        elapsed = time.time() - start_time

        if elapsed > max_wait_time:
            print(f"\n❌ 超时: 任务执行时间超过 {max_wait_time} 秒")
            break

        try:
            response = requests.get(f"{API_BASE_URL}/tasks/{video_task_id}")

            if response.status_code != 200:
                print(f"❌ 查询任务状态失败: {response.status_code}")
                break

            result = response.json()
            task = result.get("task", {})
            status = task.get("status")
            elapsed_seconds = task.get("elapsed_seconds", 0)

            print(f"   状态: {status} | 已用时: {elapsed_seconds}秒", end="\r")

            if status == "completed":
                print()
                print(f"\n🎉 视频生成完成!")
                print(f"   总耗时: {elapsed_seconds} 秒")

                # 显示输出文件信息
                if task.get("output_files"):
                    print(f"\n📹 输出文件:")
                    for idx, file_info in enumerate(task["output_files"], 1):
                        print(f"   {idx}. {file_info['filename']}")
                        print(f"      路径: {file_info['path']}")
                        print(f"      子目录: {file_info['subfolder']}")

                # 显示视频路径
                if task.get("video_path"):
                    print(f"\n🎬 视频路径: {task['video_path']}")

                break

            elif status == "failed":
                print()
                print(f"\n❌ 视频生成失败")
                if task.get("error"):
                    print(f"   错误信息: {task['error']}")
                break

            time.sleep(poll_interval)

        except requests.RequestException as e:
            print(f"\n❌ 查询任务状态出错: {e}")
            break
        except KeyError as e:
            print(f"\n❌ 响应格式错误: {e}")
            break


def main():
    """主函数 - 测试不同数量的图片"""

    print("🎬 多图片视频生成测试")
    print("=" * 60)

    # 测试场景
    test_cases = [
        {"num_images": 4, "description": "最小数量 (4张)"},
        {"num_images": 6, "description": "中等数量 (6张)"},
        {"num_images": 10, "description": "最大数量 (10张)"},
    ]

    print("\n可用的测试场景:")
    for idx, case in enumerate(test_cases, 1):
        print(f"  {idx}. {case['description']} - {case['num_images']} 张图片")

    print(f"\n请选择测试场景 (1-{len(test_cases)})，或输入自定义数量 (4-10): ", end="")

    try:
        choice = input().strip()

        if choice.isdigit():
            choice_num = int(choice)

            if 1 <= choice_num <= len(test_cases):
                # 选择预设场景
                case = test_cases[choice_num - 1]
                num_images = case["num_images"]
            elif 4 <= choice_num <= 10:
                # 自定义数量
                num_images = choice_num
            else:
                print("❌ 无效的选择")
                return
        else:
            print("❌ 请输入数字")
            return

        # 执行测试
        test_video_with_n_images(num_images=num_images)

    except KeyboardInterrupt:
        print("\n\n⚠️  测试已取消")
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
