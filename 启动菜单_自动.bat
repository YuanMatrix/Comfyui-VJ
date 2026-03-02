@echo off
chcp 65001 >nul
color 0B
cls

REM ComfyUI 自动启动脚本 - ComfyUI + VJ API（智能等待模式）

echo.
echo ================================================================
echo                    ComfyUI 自动启动
echo ================================================================
echo.
echo  启动模式: ComfyUI + VJ API (智能等待 - 30分钟超时)
echo ================================================================
echo.

cd /d "%~dp0"

echo [1/3] 启动 ComfyUI...
start "ComfyUI Server" .\python_embeded\python.exe -s ComfyUI\main.py --windows-standalone-build

echo [2/3] 等待 ComfyUI 启动...
echo.

set /a counter=0
:CHECK_LOOP
timeout /t 5 /nobreak >nul
set /a counter+=5

curl -s http://localhost:8188/system_stats >nul 2>&1
if errorlevel 1 (
    if %counter% lss 1800 (
        echo   等待中... (%counter%/1800 秒^)
        goto CHECK_LOOP
    ) else (
        echo.
        echo [!] ComfyUI 启动时间较长，继续启动 VJ API...
        echo.
        goto START_VJ
    )
)

echo.
echo [OK] ComfyUI 启动成功!
echo.

:START_VJ
echo [3/3] 启动 VJ API 服务...
start "VJ API Service" cmd /k "cd ComfyUI\vj && start_vj_api.bat"

echo.
echo ================================================================
echo [OK] 所有服务已启动!
echo.
echo  ComfyUI:  http://localhost:8188
echo  VJ API:   http://localhost:5002
echo ================================================================
echo.
echo 按任意键退出...
pause >nul
exit
