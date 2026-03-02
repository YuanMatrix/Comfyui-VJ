@echo off
chcp 65001 >nul

REM VJ Video Generation API Startup Script (Windows)

echo ==========================================
echo  VJ Video Generation API
echo ==========================================
echo.

REM Switch to script directory
cd /d "%~dp0"

REM Check Python environment
echo [1] Checking Python...
set PYTHON_PATH=..\..\python_embeded\python.exe

if not exist "%PYTHON_PATH%" (
    echo [ERROR] Python not found
    echo Path: %PYTHON_PATH%
    echo.
    pause
    exit /b 1
)

echo [OK] Python: %PYTHON_PATH%
echo.

REM Check dependencies
echo [2] Checking dependencies...

REM Check Flask
"%PYTHON_PATH%" -c "import flask" 2>nul
if errorlevel 1 (
    echo Installing Flask...
    "%PYTHON_PATH%" -m pip install Flask==3.0.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        echo [ERROR] Flask install failed
        pause
        exit /b 1
    )
)

REM Check flask-cors
"%PYTHON_PATH%" -c "import flask_cors" 2>nul
if errorlevel 1 (
    echo Installing flask-cors...
    "%PYTHON_PATH%" -m pip install flask-cors==4.0.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        echo [ERROR] flask-cors install failed
        pause
        exit /b 1
    )
)

REM Check requests
"%PYTHON_PATH%" -c "import requests" 2>nul
if errorlevel 1 (
    echo Installing requests...
    "%PYTHON_PATH%" -m pip install requests==2.31.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        echo [ERROR] requests install failed
        pause
        exit /b 1
    )
)

REM Check websocket-client
"%PYTHON_PATH%" -c "import websocket" 2>nul
if errorlevel 1 (
    echo Installing websocket-client...
    "%PYTHON_PATH%" -m pip install websocket-client==1.7.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        echo [ERROR] websocket-client install failed
        pause
        exit /b 1
    )
)

echo [OK] All dependencies installed
echo.

REM Check ComfyUI status
echo [3] Checking ComfyUI...
curl -s http://localhost:8188/system_stats >nul 2>&1
if errorlevel 1 (
    echo [WARN] ComfyUI is not running
    echo Please start ComfyUI first
    echo.
) else (
    echo [OK] ComfyUI is running
)
echo.

REM Start API service
echo [4] Starting VJ API...
echo ==========================================
echo.

REM Save current directory (vj directory)
set VJ_DIR=%CD%

REM Enter ComfyUI root directory
cd ..
set COMFYUI_DIR=%CD%

REM Set PYTHONPATH
set PYTHONPATH=%COMFYUI_DIR%;%PYTHONPATH%

REM Set full Python path
set FULL_PYTHON_PATH=%COMFYUI_DIR%\..\python_embeded\python.exe

echo Starting server...
echo ComfyUI dir: %COMFYUI_DIR%
echo Python path: %FULL_PYTHON_PATH%
echo API address: http://localhost:5002
echo.

REM Start with absolute path
"%FULL_PYTHON_PATH%" "%COMFYUI_DIR%\vj\video_generation_api.py"

REM If API service exits, pause to see error
echo.
echo ==========================================
echo API service stopped
echo.
pause
