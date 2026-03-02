#!/bin/bash

# VJ 视频生成 API 启动脚本

echo "=========================================="
echo "🎬 VJ 视频生成 API 启动"
echo "=========================================="

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，请先创建: python3 -m venv venv"
    exit 1
fi

# 激活虚拟环境
echo "📦 激活虚拟环境..."
source venv/bin/activate

# 检查依赖
echo "🔍 检查依赖..."
# 使用 python 检查模块是否已安装，避免 Broken pipe 错误
python3 -c "import flask" 2>/dev/null || pip install Flask -i https://pypi.tuna.tsinghua.edu.cn/simple
python3 -c "import flask_cors" 2>/dev/null || pip install flask-cors -i https://pypi.tuna.tsinghua.edu.cn/simple
python3 -c "import requests" 2>/dev/null || pip install requests -i https://pypi.tuna.tsinghua.edu.cn/simple
python3 -c "import websocket" 2>/dev/null || pip install websocket-client -i https://pypi.tuna.tsinghua.edu.cn/simple

# 检查 ComfyUI 是否运行
echo "🔍 检查 ComfyUI 状态..."
if ! curl -s http://localhost:8188/system_stats > /dev/null 2>&1; then
    echo "⚠️  警告: ComfyUI 未运行"
    echo "请先启动 ComfyUI: python main.py"
    echo ""
    read -p "按回车继续启动 API 服务（如果 ComfyUI 稍后会启动）..."
fi

# 启动 API 服务
echo "🚀 启动 VJ API 服务..."
echo "=========================================="

# 设置 PYTHONPATH 确保可以导入 vj 模块
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 从 ComfyUI 根目录启动
cd "$(dirname "$0")/.."
python3 vj/video_generation_api.py
