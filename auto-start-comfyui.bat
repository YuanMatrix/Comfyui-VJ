@echo off
chcp 65001 >nul

REM ComfyUI + VJ API 开机自启动脚本（非交互式，模式2）

cd /d "%~dp0"

REM 启动 ComfyUI
start "ComfyUI Server" .\python_embeded\python.exe -s ComfyUI\main.py --windows-standalone-build

REM 等待 ComfyUI 启动
set /a counter=0
:CHECK_LOOP
timeout /t 5 /nobreak >nul
set /a counter+=5

curl -s http://localhost:8188/system_stats >nul 2>&1
if errorlevel 1 (
    if %counter% lss 1800 (
        goto CHECK_LOOP
    )
)

REM 启动 VJ API
start "VJ API Service" cmd /c "cd ComfyUI\vj && start_vj_api.bat"
