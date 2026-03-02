@echo off
chcp 65001 >nul

REM ComfyUI + VJ API 启动脚本（简化版）
REM 快速启动，不等待 ComfyUI 完全启动

echo ========================================
echo ComfyUI + VJ API 快速启动
echo ========================================
echo.

cd /d "%~dp0"

REM 启动 ComfyUI
echo [1/2] 启动 ComfyUI...
start "ComfyUI Server" .\python_embeded\python.exe -s ComfyUI\main.py --windows-standalone-build

REM 等待几秒让 ComfyUI 开始启动
timeout /t 10 /nobreak >nul

REM 启动 VJ API
echo [2/2] 启动 VJ API 服务...
start "VJ API Service" cmd /k "cd ComfyUI\vj && start_vj_api.bat"

echo.
echo ✓ 服务已启动！
echo.
echo ComfyUI:  http://localhost:8188
echo VJ API:   http://localhost:5000
echo.
pause
