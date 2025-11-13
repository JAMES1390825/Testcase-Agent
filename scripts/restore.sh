#!/bin/bash
# 测试用例生成系统 - 恢复脚本
# 从备份恢复数据库和应用数据

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

BACKUP_DIR="./backups"

echo -e "${YELLOW}================================${NC}"
echo -e "${YELLOW}测试用例生成系统 - 数据恢复${NC}"
echo -e "${YELLOW}================================${NC}"

# 检查备份名称参数
if [ -z "$1" ]; then
    echo -e "${RED}错误: 请指定备份名称${NC}"
    echo ""
    echo -e "用法: $0 <backup_name>"
    echo ""
    echo -e "可用的备份:"
    ls -1 "${BACKUP_DIR}" | grep "testcase_backup_" | sed 's/_postgres.sql.gz//' | sed 's/_data.tar.gz//' | sed 's/_config.tar.gz//' | sort -u
    exit 1
fi

BACKUP_NAME="$1"

# 检查备份文件是否存在
if [ ! -f "${BACKUP_DIR}/${BACKUP_NAME}_postgres.sql.gz" ]; then
    echo -e "${RED}错误: 备份文件不存在: ${BACKUP_NAME}${NC}"
    echo -e "请检查备份目录: ${BACKUP_DIR}"
    exit 1
fi

# 警告提示
echo -e "${RED}警告: 恢复操作将覆盖当前数据！${NC}"
echo -e "${RED}建议先备份当前数据！${NC}"
echo ""
read -p "确认继续恢复？(yes/no) " -r
if [[ ! $REPLY == "yes" ]]; then
    echo -e "${YELLOW}已取消${NC}"
    exit 0
fi

# 加载环境变量
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

POSTGRES_USER=${POSTGRES_USER:-testcase}
POSTGRES_DB=${POSTGRES_DB:-testcase_agent}

# 检查服务状态
if ! docker compose ps postgres | grep -q "Up"; then
    echo -e "${YELLOW}PostgreSQL 服务未运行，正在启动...${NC}"
    docker compose up -d postgres
    echo -e "${GREEN}等待 PostgreSQL 启动...${NC}"
    sleep 10
fi

# 1. 恢复数据库
echo -e "${GREEN}[1/3] 恢复 PostgreSQL 数据库...${NC}"
echo -e "${YELLOW}停止应用服务（避免连接冲突）...${NC}"
docker compose stop app || true

echo -e "${YELLOW}删除旧数据库...${NC}"
docker compose exec -T postgres psql -U "${POSTGRES_USER}" -c "DROP DATABASE IF EXISTS ${POSTGRES_DB};"
docker compose exec -T postgres psql -U "${POSTGRES_USER}" -c "CREATE DATABASE ${POSTGRES_DB};"

echo -e "${YELLOW}导入数据库备份...${NC}"
gunzip < "${BACKUP_DIR}/${BACKUP_NAME}_postgres.sql.gz" | \
    docker compose exec -T postgres psql -U "${POSTGRES_USER}" "${POSTGRES_DB}"

echo -e "${GREEN}✓ 数据库恢复完成${NC}"

# 2. 恢复应用数据
if [ -f "${BACKUP_DIR}/${BACKUP_NAME}_data.tar.gz" ]; then
    echo -e "${GREEN}[2/3] 恢复应用数据...${NC}"
    
    # 备份当前数据
    if [ -d "data" ]; then
        echo -e "${YELLOW}备份当前数据到 data.backup...${NC}"
        mv data data.backup.$(date +%Y%m%d_%H%M%S)
    fi
    
    # 解压备份数据
    tar -xzf "${BACKUP_DIR}/${BACKUP_NAME}_data.tar.gz"
    echo -e "${GREEN}✓ 应用数据恢复完成${NC}"
else
    echo -e "${YELLOW}[2/3] 未找到应用数据备份，跳过${NC}"
fi

# 3. 恢复配置文件（可选）
if [ -f "${BACKUP_DIR}/${BACKUP_NAME}_config.tar.gz" ]; then
    echo -e "${GREEN}[3/3] 恢复配置文件（可选）...${NC}"
    read -p "是否恢复配置文件？(y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        tar -xzf "${BACKUP_DIR}/${BACKUP_NAME}_config.tar.gz"
        echo -e "${GREEN}✓ 配置文件恢复完成${NC}"
    else
        echo -e "${YELLOW}跳过配置文件恢复${NC}"
    fi
else
    echo -e "${YELLOW}[3/3] 未找到配置文件备份，跳过${NC}"
fi

# 重启服务
echo -e "${GREEN}重启所有服务...${NC}"
docker compose up -d

# 等待服务启动
echo -e "${GREEN}等待服务启动...${NC}"
sleep 10

# 检查健康状态
if curl -f http://localhost/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 服务健康检查通过${NC}"
else
    echo -e "${YELLOW}警告: 服务健康检查失败${NC}"
    echo -e "请检查日志: ${YELLOW}docker compose logs app${NC}"
fi

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}恢复完成！${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "请测试应用功能，确保数据正确恢复"
echo -e "查看日志: ${YELLOW}docker compose logs -f${NC}"
echo ""
