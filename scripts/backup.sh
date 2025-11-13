#!/bin/bash
# 测试用例生成系统 - 备份脚本
# 备份 PostgreSQL 数据库和应用数据

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 配置
BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="testcase_backup_${DATE}"
MAX_BACKUPS=7  # 保留最近 7 个备份

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}测试用例生成系统 - 数据备份${NC}"
echo -e "${GREEN}================================${NC}"

# 创建备份目录
mkdir -p "${BACKUP_DIR}"

# 检查服务是否运行
if ! docker compose ps postgres | grep -q "Up"; then
    echo -e "${RED}错误: PostgreSQL 服务未运行${NC}"
    echo -e "${YELLOW}请先启动服务: ./scripts/deploy.sh${NC}"
    exit 1
fi

# 加载环境变量
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

POSTGRES_USER=${POSTGRES_USER:-testcase}
POSTGRES_DB=${POSTGRES_DB:-testcase_agent}

# 1. 备份 PostgreSQL 数据库
echo -e "${GREEN}[1/3] 备份 PostgreSQL 数据库...${NC}"
docker compose exec -T postgres pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" \
    | gzip > "${BACKUP_DIR}/${BACKUP_NAME}_postgres.sql.gz"
echo -e "${GREEN}✓ 数据库备份完成: ${BACKUP_NAME}_postgres.sql.gz${NC}"

# 2. 备份应用数据（知识库文档、上传文件等）
echo -e "${GREEN}[2/3] 备份应用数据...${NC}"
if [ -d "data" ]; then
    tar -czf "${BACKUP_DIR}/${BACKUP_NAME}_data.tar.gz" data/
    echo -e "${GREEN}✓ 应用数据备份完成: ${BACKUP_NAME}_data.tar.gz${NC}"
else
    echo -e "${YELLOW}警告: data 目录不存在，跳过${NC}"
fi

# 3. 备份配置文件
echo -e "${GREEN}[3/3] 备份配置文件...${NC}"
tar -czf "${BACKUP_DIR}/${BACKUP_NAME}_config.tar.gz" \
    .env docker-compose.yml nginx/ 2>/dev/null || true
echo -e "${GREEN}✓ 配置文件备份完成: ${BACKUP_NAME}_config.tar.gz${NC}"

# 创建备份清单
echo "Backup created at: $(date)" > "${BACKUP_DIR}/${BACKUP_NAME}_info.txt"
echo "Database: ${POSTGRES_DB}" >> "${BACKUP_DIR}/${BACKUP_NAME}_info.txt"
echo "Files:" >> "${BACKUP_DIR}/${BACKUP_NAME}_info.txt"
ls -lh "${BACKUP_DIR}/${BACKUP_NAME}_"* >> "${BACKUP_DIR}/${BACKUP_NAME}_info.txt"

# 清理旧备份
echo -e "${GREEN}清理旧备份（保留最近 ${MAX_BACKUPS} 个）...${NC}"
cd "${BACKUP_DIR}"
# 列出所有备份，按时间排序，删除超过 MAX_BACKUPS 的旧备份
ls -t | grep "testcase_backup_" | tail -n +$((MAX_BACKUPS * 3 + 1)) | xargs -r rm -f
cd - > /dev/null

# 显示备份信息
echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}备份完成！${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "备份位置: ${GREEN}${BACKUP_DIR}/${NC}"
echo -e "备份名称: ${GREEN}${BACKUP_NAME}${NC}"
echo ""
echo -e "文件列表:"
ls -lh "${BACKUP_DIR}/${BACKUP_NAME}_"*
echo ""
echo -e "恢复备份: ${YELLOW}./scripts/restore.sh ${BACKUP_NAME}${NC}"
echo ""
echo -e "${YELLOW}建议:${NC}"
echo -e "1. 定期将备份文件复制到远程存储（OSS、S3 等）"
echo -e "2. 使用 crontab 设置自动备份任务"
echo -e "   例如: ${YELLOW}0 2 * * * /path/to/scripts/backup.sh${NC}"
echo ""
