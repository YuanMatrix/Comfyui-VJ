@echo off
chcp 65001 >nul
color 0B
cls

REM ComfyUI 启动菜单 - 支持多种启动模式

:MENU
cls
echo.
echo ╔════════════════════════════════════════════════════════════════════╗
echo ║                                                                    ║
echo ║                    ComfyUI 启动菜单                                ║
echo ║                                                                    ║
echo ╚════════════════════════════════════════════════════════════════════╝
echo.
echo  请选择启动模式:
echo.
echo  [1] 仅启动 ComfyUI（标准模式）
echo  [2] ComfyUI + VJ API（智能等待）⭐ 推荐
echo  [3] ComfyUI + VJ API（快速启动）
echo  [4] 仅启动 VJ API（ComfyUI 已运行时使用）
echo.
echo  [Q] 退出
echo.
echo ════════════════════════════════════════════════════════════════════
echo.

set /p choice="输入选项 [1-4/Q]: "

if /i "%choice%"=="1" goto COMFYUI_ONLY
if /i "%choice%"=="2" goto COMFYUI_WITH_VJ
if /i "%choice%"=="3" goto COMFYUI_WITH_VJ_QUICK
if /i "%choice%"=="4" goto VJ_ONLY
if /i "%choice%"=="Q" goto END

echo.
echo 无效的选项，请重新选择
timeout /t 2 >nul
goto MENU

REM ========================================
REM 模式 1: 仅启动 ComfyUI
REM ========================================
:COMFYUI_ONLY
cls
echo.
echo ════════════════════════════════════════════════════════════════════
echo  启动模式: 仅 ComfyUI
echo ════════════════════════════════════════════════════════════════════
echo.

cd /d "%~dp0"
.\python_embeded\python.exe -s ComfyUI\main.py --windows-standalone-build

echo.
echo If you see this and ComfyUI did not start, try updating your Nvidia
echo Drivers to the latest. If you get a c10.dll error you need to install
echo vc redist that you can find: https://aka.ms/vc14/vc_redist.x64.exe
echo.
pause
goto MENU

REM ========================================
REM 模式 2: ComfyUI + VJ API（智能等待）
REM ========================================
:COMFYUI_WITH_VJ
cls
echo.
echo ════════════════════════════════════════════════════════════════════
echo  启动模式: ComfyUI + VJ API（智能等待）
echo ════════════════════════════════════════════════════════════════════
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
    if %counter% lss 60 (
        echo   等待中... (%counter%/60 秒^)
        goto CHECK_LOOP
    ) else (
        echo.
        echo ⚠️  ComfyUI 启动时间较长，继续启动 VJ API...
        echo.
        goto START_VJ
    )
)

echo.
echo ✓ ComfyUI 启动成功！
echo.

:START_VJ
echo [3/3] 启动 VJ API 服务...
start "VJ API Service" cmd /k "cd ComfyUI\vj && start_vj_api.bat"

echo.
echo ════════════════════════════════════════════════════════════════════
echo ✓ 所有服务已启动！
echo.
echo 📌 ComfyUI:  http://localhost:8188
echo 📌 VJ API:   http://localhost:5002
echo ════════════════════════════════════════════════════════════════════
echo.
pause
goto MENU

REM ========================================
REM 模式 3: ComfyUI + VJ API（快速启动）
REM ========================================
:COMFYUI_WITH_VJ_QUICK
cls
echo.
echo ════════════════════════════════════════════════════════════════════
echo  启动模式: ComfyUI + VJ API（快速启动）
echo ════════════════════════════════════════════════════════════════════
echo.

cd /d "%~dp0"

echo [1/2] 启动 ComfyUI...
start "ComfyUI Server" .\python_embeded\python.exe -s ComfyUI\main.py --windows-standalone-build

echo [2/2] 等待 10 秒后启动 VJ API...
timeout /t 10 /nobreak >nul

start "VJ API Service" cmd /k "cd ComfyUI\vj && start_vj_api.bat"

echo.
echo ✓ 服务已启动！
echo.
echo ComfyUI:  http://localhost:8188
echo VJ API:   http://localhost:5002
echo.
pause
goto MENU

REM ========================================
REM 模式 4: 仅启动 VJ API
REM ========================================
:VJ_ONLY
cls
echo.
echo ════════════════════════════════════════════════════════════════════
echo  启动模式: 仅 VJ API
echo ════════════════════════════════════════════════════════════════════
echo.

cd /d "%~dp0"

echo 检查 ComfyUI 是否运行...
curl -s http://localhost:8188/system_stats >nul 2>&1
if errorlevel 1 (
    echo.
    echo ⚠️  警告: 未检测到 ComfyUI 运行
    echo    请确保 ComfyUI 正在运行，否则 VJ API 可能无法正常工作
    echo.
    set /p confirm="是否继续启动 VJ API? (Y/N): "
    if /i not "%confirm%"=="Y" goto MENU
)

echo.
echo 启动 VJ API 服务...
cd ComfyUI\vj
call start_vj_api.bat

pause
goto MENU

REM ========================================
REM 退出
REM ========================================
:END
cls
echo.
echo 感谢使用！
echo.
timeout /t 1 >nul
exit
