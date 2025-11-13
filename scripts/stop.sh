#!/bin/bash
# 测试用例生成系统 - 停止脚本
# 安全停止所有 Docker 服务

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}================================${NC}"
echo -e "${YELLOW}停止测试用例生成系统${NC}"
echo -e "${YELLOW}================================${NC}"

# 检查是否有运行中的容器
if ! docker compose ps --services --filter "status=running" | grep -q .; then
    echo -e "${YELLOW}没有运行中的容器${NC}"
    exit 0
fi

# 显示运行中的容器
echo -e "${GREEN}当前运行的服务:${NC}"
docker compose ps

# 询问是否继续
read -p "确认停止所有服务？(y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}已取消${NC}"
    exit 0
fi

# 优雅停止（默认 10 秒超时）
echo -e "${GREEN}正在停止服务...${NC}"
docker compose stop

# 移除容器（保留数据卷）
echo -e "${GREEN}移除容器...${NC}"
docker compose down

echo -e "${GREEN}✓ 所有服务已停止${NC}"
echo ""
echo -e "${YELLOW}注意:${NC}"
echo -e "- 数据卷已保留（postgres_data, redis_data, app_data）"
echo -e "- 如需完全清理（包括数据），使用: ${RED}docker compose down -v${NC}"
echo -e "- 重新启动服务: ${GREEN}./scripts/deploy.sh${NC}"
echo ""
