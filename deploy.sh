#!/bin/bash
# CabbageEditor AI 服务快速启动脚本

set -e

echo "=========================================="
echo "CabbageEditor AI 服务部署脚本"
echo "=========================================="

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: 未安装 Docker${NC}"
    exit 1
fi

# 检查 Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}错误: 未安装 Docker Compose${NC}"
    exit 1
fi

# 配置公网 IP
if [ -z "$PUBLIC_IP" ]; then
    echo -e "${YELLOW}提示: 未设置 PUBLIC_IP 环境变量${NC}"
    read -p "请输入公网 IP (默认: 175.24.227.58): " input_ip
    PUBLIC_IP=${input_ip:-175.24.227.58}
    export PUBLIC_IP
fi

echo -e "${GREEN}公网 IP: $PUBLIC_IP${NC}"

# 构建并启动
echo ""
echo "正在构建镜像..."
docker-compose build

echo ""
echo "正在启动服务..."
docker-compose up -d

# 等待服务启动
echo ""
echo "等待服务启动..."
sleep 5

# 检查健康状态
echo ""
echo "检查服务健康状态..."
if curl -s http://localhost:20100/healthz > /dev/null; then
    echo -e "${GREEN}✓ 服务启动成功！${NC}"
    echo ""
    echo "=========================================="
    echo "服务信息："
    echo "  - 服务地址: http://$PUBLIC_IP:20100"
    echo "  - 健康检查: http://$PUBLIC_IP:20100/healthz"
    echo "  - 查看日志: docker-compose logs -f"
    echo "  - 停止服务: docker-compose down"
    echo "=========================================="
else
    echo -e "${RED}✗ 服务启动失败${NC}"
    echo "查看日志: docker-compose logs"
    exit 1
fi

