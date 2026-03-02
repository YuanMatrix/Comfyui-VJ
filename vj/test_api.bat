@echo off
chcp 65001 >nul

echo ========================================
echo 测试 VJ API 服务
echo ========================================
echo.

echo 1. 测试健康检查端点...
curl -s http://localhost:5002/health
echo.
echo.

echo 2. 查看所有任务...
curl -s http://localhost:5002/api/tasks
echo.
echo.

echo ========================================
echo 测试完成
echo ========================================
echo.
echo 如果看到 JSON 响应，说明 API 正常工作！
echo.
pause
