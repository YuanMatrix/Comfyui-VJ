@echo off
REM VJ API 启动脚本 - 在新窗口中运行并显示完整日志

cd /d "%~dp0"

REM 在新窗口中启动 VJ API
start "VJ API Service - http://localhost:5002" cmd /k "cd /d "%~dp0" && start_vj_api.bat"

echo ✓ VJ API 服务已在新窗口中启动
echo.
echo 窗口标题: VJ API Service - http://localhost:5002
echo 服务地址: http://localhost:5002
echo.
echo 在新窗口中可以看到完整的运行日志
echo 关闭新窗口即可停止服务
echo.
pause
