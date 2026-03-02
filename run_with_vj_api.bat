@echo off
chcp 65001 >nul

REM ComfyUI + VJ API 一键启动脚本
REM 同时启动 ComfyUI 和 VJ 视频生成 API 服务

color 0B
cls

echo ╔════════════════════════════════════════════════════════════════════╗
echo ║                                                                    ║
echo ║           ComfyUI + VJ API 一键启动                                ║
echo ║                                                                    ║
echo ╚════════════════════════════════════════════════════════════════════╝
echo.
echo 🚀 正在启动服务...
echo.

REM 切换到脚本所在目录
cd /d "%~dp0"

REM 第一步：启动 ComfyUI（在新窗口）
echo [1/3] 启动 ComfyUI...
start "ComfyUI Server" .\python_embeded\python.exe -s ComfyUI\main.py --windows-standalone-build

REM 第二步：等待 ComfyUI 启动
echo [2/3] 等待 ComfyUI 启动（大约需要 20-30 秒）...
echo.
echo 正在检测 ComfyUI 状态...

REM 循环检测 ComfyUI 是否启动（最多等待 60 秒）
set /a counter=0
:CHECK_COMFYUI
timeout /t 5 /nobreak >nul
set /a counter+=5

REM 尝试连接 ComfyUI
curl -s http://localhost:8188/system_stats >nul 2>&1
if errorlevel 1 (
    if %counter% lss 60 (
        echo   等待中... (%counter%/60 秒^)
        goto CHECK_COMFYUI
    ) else (
        echo.
        echo ⚠️  警告: ComfyUI 启动时间较长或启动失败
        echo    VJ API 将继续启动，但可能需要等待 ComfyUI 完全启动后才能正常工作
        echo.
        timeout /t 3 >nul
        goto START_VJ_API
    )
)

echo.
echo ✓ ComfyUI 启动成功！
echo.

:START_VJ_API
REM 第三步：启动 VJ API（在新窗口）
echo [3/3] 启动 VJ API 服务...
start "VJ API Service" cmd /k "cd ComfyUI\vj && start_vj_api.bat"

echo.
echo ════════════════════════════════════════════════════════════════════
echo.
echo ✓ 所有服务已启动！
echo.
echo 📌 服务地址:
echo    • ComfyUI:  http://localhost:8188
echo    • VJ API:   http://localhost:5000
echo.
echo 💡 提示:
echo    • ComfyUI 窗口: 显示 ComfyUI 运行日志
echo    • VJ API 窗口: 显示 API 服务日志
echo    • 关闭任一窗口将停止对应服务
echo.
echo 🔍 如果遇到问题:
echo    1. 检查 ComfyUI 窗口是否有错误信息
echo    2. 确保没有其他程序占用 8188 或 5000 端口
echo    3. 查看 VJ API 窗口的详细日志
echo.
echo ════════════════════════════════════════════════════════════════════
echo.
echo 按任意键关闭此启动窗口（不会影响已启动的服务）
pause >nul
