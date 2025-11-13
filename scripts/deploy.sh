#!/bin/bash
# 测试用例生成系统 - 部署脚本
# 用于首次部署或更新部署到服务器

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}测试用例生成系统 - 部署脚本${NC}"
echo -e "${GREEN}================================${NC}"

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker 未安装${NC}"
    echo "请先安装 Docker: https://docs.docker.com/engine/install/"
    exit 1
fi

# 检查 Docker Compose 是否安装
if ! command -v docker compose &> /dev/null; then
    echo -e "${RED}错误: Docker Compose 未安装${NC}"
    echo "请先安装 Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# 检查 .env 文件
if [ ! -f .env ]; then
    echo -e "${YELLOW}警告: .env 文件不存在${NC}"
    echo -e "${YELLOW}正在从 .env.example 创建 .env...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✓ 已创建 .env 文件${NC}"
    echo -e "${YELLOW}请编辑 .env 文件，填写必要的配置（API keys, 密码等）${NC}"
    echo -e "${YELLOW}编辑完成后，请重新运行此脚本${NC}"
    exit 0
fi

# 创建必要的目录
echo -e "${GREEN}创建数据目录...${NC}"
mkdir -p data/kb data/uploads logs logs/nginx backups

# 拉取最新镜像
echo -e "${GREEN}拉取 Docker 镜像...${NC}"
docker compose pull postgres redis nginx

# 构建应用镜像
echo -e "${GREEN}构建应用镜像...${NC}"
docker compose build app

# 停止旧容器（如果存在）
echo -e "${GREEN}停止旧容器...${NC}"
docker compose down || true

# 启动所有服务
echo -e "${GREEN}启动服务...${NC}"
docker compose up -d

# 等待服务启动
echo -e "${GREEN}等待服务启动（最多 60 秒）...${NC}"
for i in {1..60}; do
    if docker compose ps | grep -q "healthy"; then
        break
    fi
    sleep 1
    echo -n "."
done
echo ""

# 检查服务状态
echo -e "${GREEN}检查服务状态...${NC}"
docker compose ps

# 等待应用完全启动
sleep 5

# 测试健康检查端点
echo -e "${GREEN}测试应用健康状态...${NC}"
if curl -f http://localhost/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 应用健康检查通过${NC}"
else
    echo -e "${YELLOW}警告: 应用健康检查失败，请检查日志${NC}"
    echo -e "${YELLOW}运行 'docker compose logs app' 查看详细日志${NC}"
fi

# 显示访问信息
echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}部署完成！${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "访问地址: ${GREEN}http://localhost${NC}"
echo -e "API 文档: ${GREEN}http://localhost/api/health${NC}"
echo ""
echo -e "查看日志: ${YELLOW}docker compose logs -f${NC}"
echo -e "查看特定服务日志: ${YELLOW}docker compose logs -f app${NC}"
echo -e "停止服务: ${YELLOW}docker compose down${NC}"
echo -e "重启服务: ${YELLOW}docker compose restart${NC}"
echo ""
echo -e "${GREEN}提示:${NC}"
echo -e "1. 首次部署后，请访问应用并测试所有功能"
echo -e "2. 建议设置定期备份，使用 ${YELLOW}./scripts/backup.sh${NC}"
echo -e "3. 生产环境建议配置 HTTPS（参考 DEPLOYMENT.md）"
echo ""
