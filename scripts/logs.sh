#!/bin/bash
# 测试用例生成系统 - 日志查看脚本
# 快速查看各服务的日志

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 显示帮助信息
show_help() {
    echo -e "${GREEN}测试用例生成系统 - 日志查看工具${NC}"
    echo ""
    echo "用法: $0 [service] [options]"
    echo ""
    echo "服务 (service):"
    echo "  all       - 所有服务日志（默认）"
    echo "  app       - Flask 应用日志"
    echo "  postgres  - PostgreSQL 日志"
    echo "  redis     - Redis 日志"
    echo "  nginx     - Nginx 日志"
    echo ""
    echo "选项 (options):"
    echo "  -f, --follow    - 实时跟踪日志"
    echo "  -n NUM          - 显示最后 NUM 行（默认 100）"
    echo "  -h, --help      - 显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0                  # 查看所有服务的最后 100 行日志"
    echo "  $0 app -f           # 实时跟踪应用日志"
    echo "  $0 nginx -n 50      # 查看 Nginx 最后 50 行日志"
    echo ""
}

# 默认参数
SERVICE="all"
FOLLOW=""
LINES=100

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -f|--follow)
            FOLLOW="-f"
            shift
            ;;
        -n)
            LINES="$2"
            shift 2
            ;;
        app|postgres|redis|nginx|all)
            SERVICE="$1"
            shift
            ;;
        *)
            echo -e "${YELLOW}未知参数: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# 检查服务是否运行
if ! docker compose ps | grep -q "Up"; then
    echo -e "${YELLOW}警告: 没有运行中的服务${NC}"
    exit 1
fi

# 显示日志
echo -e "${GREEN}================================${NC}"
if [ "$SERVICE" == "all" ]; then
    echo -e "${GREEN}查看所有服务日志${NC}"
else
    echo -e "${GREEN}查看 ${SERVICE} 服务日志${NC}"
fi
echo -e "${GREEN}================================${NC}"
echo ""

if [ "$SERVICE" == "all" ]; then
    docker compose logs ${FOLLOW} --tail=${LINES}
else
    docker compose logs ${FOLLOW} --tail=${LINES} ${SERVICE}
fi
