"""
并发上传工具函数

提供高效的文件上传功能，支持：
- 并发上传多个文件
- 自动管理 task_id
- 进度跟踪
- 错误处理
"""

import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
import time


class BatchUploader:
    """批量文件上传器"""
    
    def __init__(self, base_url: str = "http://localhost:5001/api", max_workers: int = 4):
        """
        初始化上传器
        
        Args:
            base_url: API 基础 URL
            max_workers: 最大并发上传数
        """
        self.base_url = base_url
        self.max_workers = max_workers
    
    def upload_file(self, file_path: str, task_id: str, file_type: str = 'image') -> Dict:
        """
        上传单个文件
        
        Args:
            file_path: 文件路径
            task_id: 任务 ID
            file_type: 文件类型 ('image' 或 'audio')
        
        Returns:
            上传结果字典
        """
        file = Path(file_path)
        if not file.exists():
            return {
                'success': False,
                'filename': file.name,
                'error': f'文件不存在: {file_path}'
            }
        
        try:
            # 确定 MIME 类型
            if file_type == 'image':
                mime_type = 'image/jpeg'  # 可以根据扩展名自动判断
                endpoint = f"{self.base_url}/upload-image"
            else:
                mime_type = 'audio/mpeg'
                endpoint = f"{self.base_url}/upload-audio"
            
            # 打开文件并上传
            with open(file, 'rb') as f:
                files = {'file': (file.name, f, mime_type)}
                data = {'task_id': task_id}
                
                response = requests.post(endpoint, files=files, data=data)
            
            if response.status_code == 201:
                result = response.json()
                return {
                    'success': True,
                    'filename': result['filename'],
                    'relative_path': result['relative_path'],
                    'full_path': result['path'],
                    'size': result['size']
                }
            else:
                return {
                    'success': False,
                    'filename': file.name,
                    'error': response.text
                }
        
        except Exception as e:
            return {
                'success': False,
                'filename': file.name,
                'error': str(e)
            }
    
    def batch_upload(self, file_paths: List[str], task_id: str, 
                    file_type: str = 'image', show_progress: bool = True) -> Dict:
        """
        批量并发上传文件
        
        Args:
            file_paths: 文件路径列表
            task_id: 任务 ID
            file_type: 文件类型 ('image' 或 'audio')
            show_progress: 是否显示进度
        
        Returns:
            {
                'success': True/False,
                'task_id': task_id,
                'uploaded': [成功上传的文件列表],
                'failed': [失败的文件列表],
                'total': 总数,
                'success_count': 成功数,
                'failed_count': 失败数,
                'elapsed_seconds': 耗时
            }
        """
        if show_progress:
            print(f"🚀 开始并发上传 {len(file_paths)} 个文件...")
        
        start_time = time.time()
        uploaded = []
        failed = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有上传任务
            future_to_path = {
                executor.submit(self.upload_file, file_path, task_id, file_type): file_path
                for file_path in file_paths
            }
            
            # 收集结果
            completed = 0
            for future in as_completed(future_to_path):
                file_path = future_to_path[future]
                completed += 1
                
                try:
                    result = future.result()
                    
                    if result['success']:
                        uploaded.append({
                            'filename': result['filename'],
                            'relative_path': result['relative_path'],
                            'full_path': result['full_path'],
                            'size': result['size']
                        })
                        
                        if show_progress:
                            print(f"✅ [{completed}/{len(file_paths)}] {result['filename']}")
                    else:
                        failed.append({
                            'filename': result['filename'],
                            'error': result['error']
                        })
                        
                        if show_progress:
                            print(f"❌ [{completed}/{len(file_paths)}] {result['filename']}: {result['error']}")
                
                except Exception as e:
                    filename = Path(file_path).name
                    failed.append({
                        'filename': filename,
                        'error': str(e)
                    })
                    
                    if show_progress:
                        print(f"❌ [{completed}/{len(file_paths)}] {filename}: {e}")
        
        elapsed = time.time() - start_time
        
        if show_progress:
            print(f"\n⏱️  上传完成，耗时: {elapsed:.2f}s")
            print(f"   成功: {len(uploaded)}/{len(file_paths)}")
            if failed:
                print(f"   失败: {len(failed)}")
        
        return {
            'success': len(failed) == 0,
            'task_id': task_id,
            'uploaded': uploaded,
            'failed': failed,
            'total': len(file_paths),
            'success_count': len(uploaded),
            'failed_count': len(failed),
            'elapsed_seconds': elapsed
        }


# 便捷函数
def batch_upload_images(image_paths: List[str], task_id: Optional[str] = None,
                        base_url: str = "http://localhost:5001/api",
                        max_workers: int = 4) -> Dict:
    """
    批量上传图片（便捷函数）
    
    Args:
        image_paths: 图片路径列表
        task_id: 任务 ID（可选，不提供则使用第一次上传返回的）
        base_url: API 基础 URL
        max_workers: 最大并发数
    
    Returns:
        上传结果字典
    """
    import uuid
    if task_id is None:
        task_id = str(uuid.uuid4())
    
    uploader = BatchUploader(base_url, max_workers)
    return uploader.batch_upload(image_paths, task_id, file_type='image')


def batch_upload_audio(audio_paths: List[str], task_id: Optional[str] = None,
                       base_url: str = "http://localhost:5001/api",
                       max_workers: int = 4) -> Dict:
    """
    批量上传音频（便捷函数）
    
    Args:
        audio_paths: 音频路径列表
        task_id: 任务 ID（可选）
        base_url: API 基础 URL
        max_workers: 最大并发数
    
    Returns:
        上传结果字典
    """
    import uuid
    if task_id is None:
        task_id = str(uuid.uuid4())
    
    uploader = BatchUploader(base_url, max_workers)
    return uploader.batch_upload(audio_paths, task_id, file_type='audio')


# 使用示例
if __name__ == "__main__":
    # 示例 1: 使用类
    uploader = BatchUploader(base_url="http://localhost:5001/api", max_workers=4)
    
    images = [
        "/Users/coco/coco-code/ComfyUI/input/11.jpg",
        "/Users/coco/coco-code/ComfyUI/input/12.jpg",
        "/Users/coco/coco-code/ComfyUI/input/13.jpg",
        "/Users/coco/coco-code/ComfyUI/input/14.jpg"
    ]
    
    result = uploader.batch_upload(images, task_id="my-task-123", file_type='image')
    
    print(f"\n上传结果:")
    print(f"  任务 ID: {result['task_id']}")
    print(f"  成功: {result['success_count']}")
    print(f"  失败: {result['failed_count']}")
    
    # 获取相对路径列表（用于生成视频）
    image_paths = [item['relative_path'] for item in result['uploaded']]
    print(f"\n图片相对路径:")
    for path in image_paths:
        print(f"    {path}")
    
    # 示例 2: 使用便捷函数
    # result = batch_upload_images(images, task_id="another-task")
