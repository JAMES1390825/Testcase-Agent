# 测试用例生成系统 - Docker 部署快速参考

## 📦 部署文件清单

```
testcase-agent/
├── Dockerfile                    # Flask 应用容器镜像
├── docker-compose.yml            # 多服务编排配置
├── .env.example                  # 环境变量模板
├── nginx/                        # Nginx 配置
│   ├── nginx.conf               # 主配置文件
│   └── conf.d/
│       └── default.conf         # 虚拟主机配置
├── scripts/                      # 部署脚本
│   ├── deploy.sh                # 部署脚本
│   ├── stop.sh                  # 停止脚本
│   ├── backup.sh                # 备份脚本
│   ├── restore.sh               # 恢复脚本
│   └── logs.sh                  # 日志查看脚本
└── DEPLOYMENT.md                 # 完整部署文档
```

## 🚀 快速开始（5 分钟部署）

### 1. 准备环境
```bash
# 确保已安装 Docker 和 Docker Compose
docker --version
docker compose version
```

### 2. 配置环境变量
```bash
# 复制并编辑环境变量文件
cp .env.example .env
vim .env

# 必须修改的配置项：
# - OPENAI_API_KEY=your-key
# - EMBEDDING_API_KEY=your-key
# - POSTGRES_PASSWORD=strong-password
# - REDIS_PASSWORD=strong-password
```

### 3. 一键部署
```bash
# 执行部署脚本
./scripts/deploy.sh

# 部署脚本会自动：
# ✓ 检查 Docker 环境
# ✓ 创建数据目录
# ✓ 构建应用镜像
# ✓ 启动所有服务
# ✓ 执行健康检查
```

### 4. 验证部署
```bash
# 检查服务状态
docker compose ps

# 访问应用
# 浏览器打开: http://your-server-ip
# 或使用: curl http://localhost/health
```

## 🎯 核心命令速查

### 服务管理
```bash
# 启动所有服务
docker compose up -d

# 停止所有服务
./scripts/stop.sh
# 或: docker compose stop

# 重启服务
docker compose restart

# 重启特定服务
docker compose restart app

# 查看服务状态
docker compose ps

# 查看资源使用
docker stats
```

### 日志管理
```bash
# 实时查看所有日志
./scripts/logs.sh -f
# 或: docker compose logs -f

# 查看应用日志
./scripts/logs.sh app -f
# 或: docker compose logs -f app

# 查看最后 100 行日志
./scripts/logs.sh app -n 100

# 查看 Nginx 日志
./scripts/logs.sh nginx
tail -f logs/nginx/access.log
```

### 备份与恢复
```bash
# 手动备份
./scripts/backup.sh

# 列出所有备份
ls -lh backups/

# 恢复指定备份
./scripts/restore.sh testcase_backup_20240101_020000

# 设置自动备份（crontab）
0 2 * * * cd /opt/testcase-agent && ./scripts/backup.sh
```

### 更新部署
```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker compose up -d --build

# 或使用部署脚本
./scripts/deploy.sh
```

## 🔧 常见运维操作

### 进入容器
```bash
# 进入应用容器
docker compose exec app bash

# 进入数据库容器
docker compose exec postgres psql -U testcase testcase_agent

# 进入 Redis
docker compose exec redis redis-cli -a your_redis_password
```

### 数据库操作
```bash
# 连接数据库
docker compose exec postgres psql -U testcase testcase_agent

# 查看所有表
\dt

# 查看知识库文档
SELECT id, filename, created_at FROM kb_docs ORDER BY created_at DESC LIMIT 10;

# 查看上传的测试用例
SELECT id, filename, created_at FROM uploaded_testcases ORDER BY created_at DESC LIMIT 10;

# 手动备份数据库
docker compose exec -T postgres pg_dump -U testcase testcase_agent | gzip > backup_manual.sql.gz
```

### Redis 操作
```bash
# 连接 Redis
docker compose exec redis redis-cli -a your_redis_password

# 查看所有 keys
KEYS *

# 查看缓存统计
INFO stats

# 清空所有缓存（慎用！）
FLUSHALL
```

### 清理 Docker
```bash
# 清理未使用的镜像
docker image prune -a

# 清理未使用的容器
docker container prune

# 清理未使用的卷（慎用！会删除数据）
docker volume prune

# 完全清理（慎用！）
docker system prune -a --volumes
```

## 📊 监控指标

### 健康检查
```bash
# 应用健康状态
curl http://localhost/health

# 所有服务健康状态
docker compose ps
```

### 资源监控
```bash
# 实时资源使用
docker stats

# 磁盘使用
df -h

# Docker 磁盘使用
docker system df
```

## 🔐 安全检查清单

- [ ] 已修改 PostgreSQL 默认密码
- [ ] 已修改 Redis 默认密码
- [ ] 已配置有效的 API Keys
- [ ] 已配置防火墙（只开放 80/443）
- [ ] 已启用 HTTPS（生产环境）
- [ ] 已设置定期备份
- [ ] 已配置日志轮转
- [ ] 已限制 Nginx 上传文件大小（50MB）

## 🐛 快速故障排查

### 服务无法启动
```bash
# 查看详细日志
docker compose logs app

# 检查端口占用
sudo lsof -i :80
sudo lsof -i :5432

# 检查磁盘空间
df -h
```

### 应用报错
```bash
# 查看应用日志
docker compose logs -f app

# 重启应用
docker compose restart app

# 重新构建应用
docker compose up -d --build app
```

### 数据库连接失败
```bash
# 检查 PostgreSQL 状态
docker compose ps postgres

# 查看数据库日志
docker compose logs postgres

# 验证密码
docker compose exec postgres psql -U testcase testcase_agent
```

### Redis 连接失败
```bash
# 检查 Redis 状态
docker compose ps redis

# 查看 Redis 日志
docker compose logs redis

# 验证密码
docker compose exec redis redis-cli -a your_redis_password PING
```

## 📚 文档索引

- **完整部署指南**: [DEPLOYMENT.md](./DEPLOYMENT.md)
- **知识库配置**: [KB_CONFIG.md](./KB_CONFIG.md)
- **快速开始测试**: [QUICKSTART.md](./QUICKSTART.md)
- **实现总结**: [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)

## 💡 实用技巧

### 性能优化
```bash
# 增加 Gunicorn workers（编辑 Dockerfile）
# 推荐: workers = CPU 核心数 × 2 + 1

# 调整 PostgreSQL 连接池
# 编辑 backend/services/db.py

# 增加 Redis 内存限制
# 编辑 docker-compose.yml: --maxmemory 1gb
```

### 日志管理
```bash
# 设置日志轮转（编辑 /etc/logrotate.d/testcase）
/opt/testcase-agent/logs/nginx/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
}
```

### 自动化运维
```bash
# 设置定时任务（crontab -e）
# 每天凌晨 2 点备份
0 2 * * * cd /opt/testcase-agent && ./scripts/backup.sh

# 每天凌晨 3 点清理旧日志
0 3 * * * find /opt/testcase-agent/logs -name "*.log" -mtime +30 -delete

# 每 5 分钟健康检查
*/5 * * * * curl -f http://localhost/health || systemctl restart docker
```

## 🆘 获取帮助

遇到问题？
1. ✅ 查看 [DEPLOYMENT.md](./DEPLOYMENT.md) 完整文档
2. ✅ 运行 `./scripts/logs.sh -f` 查看实时日志
3. ✅ 检查 [故障排查](#-快速故障排查) 章节
4. ✅ 联系开发团队

---

**提示**: 这是快速参考文档，完整信息请查看 [DEPLOYMENT.md](./DEPLOYMENT.md)
