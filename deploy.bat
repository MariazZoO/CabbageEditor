@echo off
REM CabbageEditor AI 服务快速启动脚本 (Windows)

echo ==========================================
echo CabbageEditor AI 服务部署脚本
echo ==========================================

REM 检查 Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未安装 Docker
    pause
    exit /b 1
)

REM 检查 Docker Compose
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未安装 Docker Compose
    pause
    exit /b 1
)

REM 配置公网 IP
if "%PUBLIC_IP%"=="" (
    echo 提示: 未设置 PUBLIC_IP 环境变量
    set /p PUBLIC_IP="请输入公网 IP (默认: 175.24.227.58): "
    if "%PUBLIC_IP%"=="" set PUBLIC_IP=175.24.227.58
)

echo 公网 IP: %PUBLIC_IP%

REM 构建并启动
echo.
echo 正在构建镜像...
docker-compose build

echo.
echo 正在启动服务...
docker-compose up -d

REM 等待服务启动
echo.
echo 等待服务启动...
timeout /t 5 /nobreak >nul

REM 检查健康状态
echo.
echo 检查服务健康状态...
curl -s http://localhost:20100/healthz >nul 2>&1
if errorlevel 1 (
    echo 服务启动失败
    echo 查看日志: docker-compose logs
    pause
    exit /b 1
) else (
    echo ==========================================
    echo 服务启动成功！
    echo.
    echo 服务信息：
    echo   - 服务地址: http://%PUBLIC_IP%:20100
    echo   - 健康检查: http://%PUBLIC_IP%:20100/healthz
    echo   - 查看日志: docker-compose logs -f
    echo   - 停止服务: docker-compose down
    echo ==========================================
)

pause

