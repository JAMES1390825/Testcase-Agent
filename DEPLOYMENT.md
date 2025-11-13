# 测试用例生成系统 - 生产环境部署指南

## 目录
1. [系统架构](#系统架构)
2. [服务器准备](#服务器准备)
3. [首次部署](#首次部署)
4. [配置说明](#配置说明)
5. [运维管理](#运维管理)
6. [监控与日志](#监控与日志)
7. [备份与恢复](#备份与恢复)
8. [HTTPS 配置](#https-配置)
9. [故障排查](#故障排查)
10. [性能优化](#性能优化)

---

## 系统架构

本系统采用 Docker Compose 多服务架构，包含以下组件：

```
┌─────────────────────────────────────────────────────┐
│                     Nginx (80/443)                   │
│              反向代理 + 静态文件服务                    │
└─────────────────┬───────────────────────────────────┘
                  │
          ┌───────┴───────┐
          │               │
┌─────────▼─────────┐   ┌─▼──────────────┐
│   Flask App       │   │  Static Files   │
│   (Gunicorn)      │   │  (Frontend)     │
│   Port: 5001      │   │                 │
└─────┬─────┬───────┘   └─────────────────┘
      │     │
      │     │
┌─────▼─────▼─────┐     ┌──────────────┐
│   PostgreSQL     │     │    Redis     │
│   Port: 5432     │     │  Port: 6379  │
│  (数据持久化)     │     │  (缓存/队列)  │
└──────────────────┘     └──────────────┘
```

**数据持久化：**
- `postgres_data`: PostgreSQL 数据库文件
- `redis_data`: Redis 持久化数据
- `app_data`: 应用数据（知识库、上传文件）

---

## 服务器准备

### 1. 服务器要求

**最低配置：**
- CPU: 2 核
- 内存: 4GB
- 磁盘: 20GB SSD
- 操作系统: Ubuntu 20.04+ / CentOS 7+ / Alibaba Cloud Linux

**推荐配置：**
- CPU: 4 核
- 内存: 8GB
- 磁盘: 50GB SSD
- 操作系统: Ubuntu 22.04 LTS

### 2. 安装 Docker

**Ubuntu/Debian:**
```bash
# 更新包索引
sudo apt-get update

# 安装依赖
sudo apt-get install -y ca-certificates curl gnupg lsb-release

# 添加 Docker 官方 GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 添加 Docker 仓库
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装 Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker

# 将当前用户添加到 docker 组（可选，避免每次使用 sudo）
sudo usermod -aG docker $USER
```

**CentOS/RHEL:**
```bash
# 安装依赖
sudo yum install -y yum-utils

# 添加 Docker 仓库
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# 安装 Docker Engine
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker

# 将当前用户添加到 docker 组
sudo usermod -aG docker $USER
```

**验证安装：**
```bash
docker --version
docker compose version
```

### 3. 配置防火墙

**Ubuntu (UFW):**
```bash
# 允许 HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 如需远程访问数据库（不推荐）
# sudo ufw allow 5432/tcp

# 启用防火墙
sudo ufw enable
```

**CentOS (firewalld):**
```bash
# 允许 HTTP/HTTPS
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https

# 重载防火墙
sudo firewall-cmd --reload
```

**阿里云安全组：**
在阿里云控制台配置安全组规则：
- 入站规则：允许 80/tcp（HTTP）
- 入站规则：允许 443/tcp（HTTPS）
- 出站规则：允许所有

### 4. 配置域名（可选）

如果使用域名：
1. 在域名服务商添加 A 记录指向服务器 IP
2. 等待 DNS 解析生效（通常 5-30 分钟）
3. 验证：`ping your-domain.com`

---

## 首次部署

### 1. 获取代码

```bash
# 克隆仓库或上传代码到服务器
cd /opt
sudo git clone <your-repo-url> testcase-agent
cd testcase-agent

# 或使用 scp 上传
# scp -r ./testcase-agent root@your-server:/opt/
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置文件
vim .env
# 或
nano .env
```

**必填配置项：**
```bash
# OpenAI API（文本生成）
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
TEXT_MODEL_NAME=gpt-4o

# Embedding API（知识库向量化）
EMBEDDING_API_KEY=sk-your-embedding-api-key-here
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_MODEL=text-embedding-3-small

# 数据库密码（请修改为强密码）
POSTGRES_PASSWORD=your_secure_postgres_password_here

# Redis 密码（请修改为强密码）
REDIS_PASSWORD=your_secure_redis_password_here
```

**生成强密码：**
```bash
# 生成 32 位随机密码
openssl rand -base64 32
```

### 3. 执行部署

```bash
# 运行部署脚本
./scripts/deploy.sh
```

部署脚本会自动：
1. 检查 Docker 环境
2. 创建必要的目录
3. 拉取/构建镜像
4. 启动所有服务
5. 执行健康检查

### 4. 验证部署

```bash
# 检查服务状态
docker compose ps

# 所有服务应显示 "healthy" 或 "Up"
```

访问应用：
- 浏览器打开：`http://your-server-ip`
- 或：`http://your-domain.com`

测试 API：
```bash
curl http://localhost/health
# 应返回: {"status":"healthy"}
```

---

## 配置说明

### 环境变量详解

#### OpenAI API 配置
```bash
# OpenAI API Key（必填）
OPENAI_API_KEY=sk-xxx

# API Base URL（可选，用于代理或第三方服务）
OPENAI_BASE_URL=https://api.openai.com/v1

# 文本模型（推荐 gpt-4o）
TEXT_MODEL_NAME=gpt-4o

# 视觉模型（用于图片识别，推荐 gpt-4o）
VISION_MODEL_NAME=gpt-4o

# 多模态开关（1=禁用，0=启用）
DISABLE_VISION=1
```

#### 数据库配置
```bash
# PostgreSQL 配置
POSTGRES_USER=testcase              # 数据库用户名
POSTGRES_PASSWORD=strong_password   # 数据库密码（必须修改）
POSTGRES_DB=testcase_agent          # 数据库名称

# 连接 URL（docker-compose 自动生成）
# DATABASE_URL=postgresql+psycopg://testcase:password@postgres:5432/testcase_agent
```

#### Redis 配置
```bash
# Redis 密码（必须修改）
REDIS_PASSWORD=strong_redis_password

# 连接 URL（docker-compose 自动生成）
# REDIS_URL=redis://:password@redis:6379/0
```

#### 知识库向量化配置
```bash
# Embedding API Key（必填）
EMBEDDING_API_KEY=sk-xxx

# Embedding API Base URL
EMBEDDING_BASE_URL=https://api.openai.com/v1

# Embedding 模型（推荐 text-embedding-3-small）
EMBEDDING_MODEL=text-embedding-3-small
```

### Docker Compose 配置

如需调整服务配置，编辑 `docker-compose.yml`：

**调整资源限制：**
```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

**调整 Gunicorn Workers：**
编辑 `Dockerfile`：
```dockerfile
CMD ["gunicorn", "--workers", "8", "--bind", "0.0.0.0:5001", ...]
```
推荐 Workers 数量 = CPU 核心数 × 2 + 1

---

## 运维管理

### 启动服务
```bash
./scripts/deploy.sh
# 或
docker compose up -d
```

### 停止服务
```bash
./scripts/stop.sh
# 或
docker compose stop
```

### 重启服务
```bash
docker compose restart

# 重启特定服务
docker compose restart app
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

### 扩容服务

**水平扩展应用：**
```bash
# 启动多个 app 实例
docker compose up -d --scale app=3

# 需要配置 Nginx 负载均衡（见下方）
```

**Nginx 负载均衡配置：**
编辑 `nginx/conf.d/default.conf`：
```nginx
upstream flask_app {
    server app:5001;
    server app:5002;
    server app:5003;
}
```

---

## 监控与日志

### 查看日志

**实时查看所有日志：**
```bash
./scripts/logs.sh -f
# 或
docker compose logs -f
```

**查看特定服务日志：**
```bash
./scripts/logs.sh app -f          # Flask 应用
./scripts/logs.sh postgres -n 50  # PostgreSQL 最后 50 行
./scripts/logs.sh nginx           # Nginx
./scripts/logs.sh redis           # Redis
```

### 日志文件位置

- **Nginx 日志**: `./logs/nginx/access.log`, `./logs/nginx/error.log`
- **应用日志**: `docker compose logs app`
- **数据库日志**: `docker compose logs postgres`

### 监控服务健康

```bash
# 检查所有服务状态
docker compose ps

# 检查健康端点
curl http://localhost/health

# 查看资源使用情况
docker stats
```

### 设置监控告警（可选）

**使用 cron 定时检查：**
```bash
# 编辑 crontab
crontab -e

# 添加健康检查任务（每 5 分钟）
*/5 * * * * curl -f http://localhost/health || echo "Service unhealthy" | mail -s "Alert" admin@example.com
```

---

## 备份与恢复

### 自动备份

**设置定时备份：**
```bash
# 编辑 crontab
crontab -e

# 每天凌晨 2 点备份
0 2 * * * cd /opt/testcase-agent && ./scripts/backup.sh >> /var/log/backup.log 2>&1
```

### 手动备份

```bash
# 执行备份
./scripts/backup.sh
```

备份文件位置：`./backups/testcase_backup_YYYYMMDD_HHMMSS_*`

备份内容：
- `*_postgres.sql.gz`: PostgreSQL 数据库
- `*_data.tar.gz`: 应用数据（知识库、上传文件）
- `*_config.tar.gz`: 配置文件

### 恢复数据

```bash
# 列出可用备份
ls -lh backups/

# 恢复指定备份
./scripts/restore.sh testcase_backup_20240101_020000
```

### 远程备份（推荐）

**上传到阿里云 OSS：**
```bash
# 安装 ossutil
wget http://gosspublic.alicdn.com/ossutil/1.7.15/ossutil64
chmod +x ossutil64
sudo mv ossutil64 /usr/local/bin/ossutil

# 配置 OSS
ossutil config

# 上传备份
ossutil cp -r ./backups/ oss://your-bucket/testcase-backups/
```

**使用 rsync 同步到远程服务器：**
```bash
rsync -avz ./backups/ user@backup-server:/backup/testcase-agent/
```

---

## HTTPS 配置

### 使用 Let's Encrypt 免费证书

**1. 安装 Certbot:**
```bash
sudo apt-get update
sudo apt-get install -y certbot
```

**2. 获取证书:**
```bash
# 停止 Nginx（占用 80 端口）
docker compose stop nginx

# 获取证书
sudo certbot certonly --standalone -d your-domain.com

# 证书位置：
# /etc/letsencrypt/live/your-domain.com/fullchain.pem
# /etc/letsencrypt/live/your-domain.com/privkey.pem
```

**3. 配置 Nginx HTTPS:**

编辑 `docker-compose.yml`，添加证书挂载：
```yaml
nginx:
  volumes:
    - /etc/letsencrypt:/etc/letsencrypt:ro
```

取消注释 `nginx/conf.d/default.conf` 中的 HTTPS 配置，并修改：
```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # ... 其他配置
}

# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

**4. 重启 Nginx:**
```bash
docker compose restart nginx
```

**5. 自动续期:**
```bash
# 测试续期
sudo certbot renew --dry-run

# 设置自动续期（每天检查）
echo "0 3 * * * certbot renew --quiet && docker compose restart nginx" | sudo crontab -
```

---

## 故障排查

### 服务无法启动

**检查日志：**
```bash
docker compose logs app
```

**常见问题：**

1. **端口冲突**
   ```bash
   # 检查端口占用
   sudo lsof -i :80
   sudo lsof -i :5432
   
   # 修改 docker-compose.yml 中的端口映射
   ```

2. **磁盘空间不足**
   ```bash
   # 检查磁盘空间
   df -h
   
   # 清理 Docker
   docker system prune -a
   ```

3. **数据库连接失败**
   - 检查 `.env` 中的 `POSTGRES_PASSWORD` 是否正确
   - 查看 PostgreSQL 日志：`docker compose logs postgres`

4. **Redis 连接失败**
   - 检查 `.env` 中的 `REDIS_PASSWORD` 是否正确
   - 查看 Redis 日志：`docker compose logs redis`

### API 请求超时

1. **增加超时时间**
   编辑 `nginx/conf.d/default.conf`：
   ```nginx
   proxy_read_timeout 600s;  # 增加到 10 分钟
   ```

2. **增加 Gunicorn 超时**
   编辑 `Dockerfile`：
   ```dockerfile
   CMD ["gunicorn", "--timeout", "600", ...]
   ```

### 内存不足

```bash
# 查看内存使用
docker stats

# 限制 Redis 内存（已在 docker-compose.yml 配置）
# --maxmemory 512mb

# 调整 Gunicorn workers
# 减少 workers 数量可降低内存使用
```

### 数据库性能问题

```bash
# 进入 PostgreSQL 容器
docker compose exec postgres psql -U testcase testcase_agent

# 查看慢查询
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

# 重建索引
REINDEX DATABASE testcase_agent;
```

---

## 性能优化

### 1. 数据库优化

**编辑 docker-compose.yml，添加 PostgreSQL 配置：**
```yaml
postgres:
  command: >
    postgres
    -c shared_buffers=256MB
    -c effective_cache_size=1GB
    -c maintenance_work_mem=64MB
    -c checkpoint_completion_target=0.9
    -c wal_buffers=16MB
    -c default_statistics_target=100
    -c random_page_cost=1.1
    -c effective_io_concurrency=200
    -c work_mem=4MB
    -c min_wal_size=1GB
    -c max_wal_size=4GB
```

### 2. Redis 优化

**调整内存策略：**
```yaml
redis:
  command: >
    redis-server
    --requirepass ${REDIS_PASSWORD}
    --maxmemory 1gb
    --maxmemory-policy allkeys-lru
    --save 900 1
    --save 300 10
```

### 3. 应用优化

**增加并发 workers：**
```dockerfile
CMD ["gunicorn", "--workers", "8", "--threads", "2", ...]
```

**启用 Gzip 压缩：**
Nginx 已配置 Gzip，确保启用。

### 4. 缓存优化

**使用 Redis 缓存生成结果：**
在 `.env` 中配置缓存 TTL（已实现）。

### 5. 使用 CDN（可选）

对于静态资源，可配置 CDN 加速：
- 阿里云 CDN
- Cloudflare
- 腾讯云 CDN

---

## 安全建议

1. **修改所有默认密码**
   - PostgreSQL 密码
   - Redis 密码
   - 使用 20+ 位随机密码

2. **启用 HTTPS**
   - 使用 Let's Encrypt 免费证书
   - 强制 HTTP 重定向到 HTTPS

3. **配置防火墙**
   - 只开放必要端口（80, 443）
   - 禁止直接访问数据库端口

4. **限制 API 访问**
   - 配置 Nginx rate limiting
   - 添加 IP 白名单（如需）

5. **定期更新**
   - 更新 Docker 镜像
   - 更新系统安全补丁

6. **日志监控**
   - 定期检查异常访问
   - 设置告警通知

---

## 联系支持

如遇到问题，请：
1. 查看日志：`./scripts/logs.sh -f`
2. 检查服务状态：`docker compose ps`
3. 查阅本文档的故障排查章节
4. 联系开发团队

---

**部署完成！祝使用愉快！** 🎉
