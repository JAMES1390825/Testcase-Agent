# 云服务器部署指南（GitHub → 阿里云）

## 🎯 部署流程概述

```
本地开发 → 推送到 GitHub → 云服务器拉取代码 → 配置 .env → 启动服务
```

**重要原则：**
- ✅ `.env` 文件**不推送**到 GitHub（已在 .gitignore）
- ✅ 在云服务器上**单独创建** `.env` 文件
- ✅ 数据库和 Redis 运行在 Docker 容器中，**自动连接**

---

## 📋 部署步骤

### 步骤 1：本地推送代码到 GitHub

```bash
# 在本地（Mac）
cd /Users/xujinliang/Desktop/Testcase\ Agent

# 确认 .env 不会被提交（应该显示在 Untracked 或被忽略）
git status

# 提交其他文件
git add .
git commit -m "Update Docker deployment configuration"
git push origin main
```

**检查清单：**
- ✅ `.env` 文件不在提交列表中
- ✅ `.env.example` 已提交（作为模板）
- ✅ `docker-compose.yml` 已提交
- ✅ `scripts/` 目录下的部署脚本已提交

---

### 步骤 2：登录云服务器

```bash
# 从本地 Mac SSH 到阿里云
ssh root@47.114.100.171
```

---

### 步骤 3：在云服务器上安装 Docker（如未安装）

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release

# 添加 Docker GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 添加 Docker 仓库
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装 Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker

# 验证安装
docker --version
docker compose version
```

---

### 步骤 4：在云服务器上克隆代码

```bash
# 创建项目目录
cd /opt
sudo git clone https://github.com/JAMES1390825/Testcase-Agent.git testcase-agent
cd testcase-agent

# 给脚本添加执行权限
chmod +x scripts/*.sh
```

---

### 步骤 5：在云服务器上创建 .env 文件（⚠️ 重要）

```bash
# 在云服务器上创建 .env 文件
cd /opt/testcase-agent
cp .env.example .env

# 编辑 .env 文件
vim .env
# 或
nano .env
```

**填写配置（只需修改 2 项）：**

```bash
# === 1. PostgreSQL 数据库配置（必填） ===
POSTGRES_USER=testcase
POSTGRES_PASSWORD=你的强密码_请用openssl生成
POSTGRES_DB=testcase_agent

# === 2. Redis 缓存配置（必填） ===
REDIS_PASSWORD=你的强密码_请用openssl生成
```

**生成强密码：**
```bash
# 在云服务器上执行
openssl rand -base64 32  # PostgreSQL 密码
openssl rand -base64 32  # Redis 密码
```

---

### 步骤 6：部署服务

```bash
# 在云服务器上执行部署脚本
cd /opt/testcase-agent
./scripts/deploy.sh
```

部署脚本会自动：
1. ✅ 检查 Docker 环境
2. ✅ 创建数据目录
3. ✅ 拉取并构建镜像
4. ✅ 启动 PostgreSQL、Redis、Flask App、Nginx
5. ✅ 执行健康检查

---

### 步骤 7：验证部署

```bash
# 检查服务状态
docker compose ps

# 查看日志
docker compose logs -f

# 测试健康检查
curl http://localhost/health
```

**访问应用：**
- 浏览器打开：`http://47.114.100.171`
- 如果配置了域名：`http://your-domain.com`

---

## 🔌 数据库和 Redis 连接说明

### ✅ 为什么能自动连接？

1. **PostgreSQL 和 Redis 运行在 Docker 容器中**
   - PostgreSQL 容器名：`testcase-postgres`
   - Redis 容器名：`testcase-redis`

2. **Docker Compose 内部网络**
   - 所有服务在同一个 `testcase-network` 网络中
   - 服务之间通过**容器名**互相访问
   - 不需要使用 IP 地址

3. **连接 URL 自动构建**
   ```yaml
   # docker-compose.yml 中的配置
   environment:
     DATABASE_URL: postgresql+psycopg://testcase:${POSTGRES_PASSWORD}@postgres:5432/testcase_agent
     REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
   ```
   - `@postgres:5432` → 使用容器名 `postgres`，不是 localhost
   - `@redis:6379` → 使用容器名 `redis`，不是 localhost

4. **密码从 .env 读取**
   - `${POSTGRES_PASSWORD}` → 从 .env 文件读取
   - `${REDIS_PASSWORD}` → 从 .env 文件读取

### 🌐 Docker 网络架构

```
┌─────────────────────────────────────────┐
│   Docker Network: testcase-network      │
│                                          │
│  ┌──────────┐    ┌──────────┐          │
│  │   App    │───→│PostgreSQL│          │
│  │  :5001   │    │  :5432   │          │
│  └────┬─────┘    └──────────┘          │
│       │                                  │
│       └─────────→┌──────────┐          │
│                  │  Redis   │          │
│                  │  :6379   │          │
│                  └──────────┘          │
│                                          │
└─────────────────────────────────────────┘
         ↑
    ┌────┴────┐
    │  Nginx  │  ← 外部访问入口（80/443）
    └─────────┘
```

---

## 🔄 更新部署流程

当您在本地修改代码后：

```bash
# 1. 本地提交并推送
git add .
git commit -m "Your update message"
git push origin main

# 2. SSH 到云服务器
ssh root@47.114.100.171

# 3. 更新代码
cd /opt/testcase-agent
git pull origin main

# 4. 重新部署
./scripts/deploy.sh
```

**注意：**
- `.env` 文件不会被覆盖（不在 Git 中）
- 数据库数据不会丢失（存储在 Docker volume）
- Redis 数据不会丢失（存储在 Docker volume）

---

## 📊 数据持久化

### Docker Volumes（自动创建）

```bash
# 查看 Docker volumes
docker volume ls

# 应该看到：
# testcase-agent_postgres_data  ← PostgreSQL 数据
# testcase-agent_redis_data     ← Redis 数据
# testcase-agent_app_data       ← 应用数据（知识库、上传文件）
```

### 数据存储位置

- **PostgreSQL 数据**：Docker volume `postgres_data`
- **Redis 数据**：Docker volume `redis_data`
- **应用数据**：Docker volume `app_data` + `./data` 目录
- **日志文件**：`./logs` 目录
- **备份文件**：`./backups` 目录

**即使删除容器，数据也不会丢失**（除非使用 `docker compose down -v`）

---

## 🔒 安全建议

### 1. 防火墙配置

```bash
# 只开放 HTTP/HTTPS 端口
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# 数据库和 Redis 端口不要对外开放！
# 它们只在 Docker 内部网络中通信
```

### 2. 阿里云安全组

在阿里云控制台配置：
- ✅ 入站规则：允许 80/tcp（HTTP）
- ✅ 入站规则：允许 443/tcp（HTTPS）
- ❌ **不要**开放 5432（PostgreSQL）
- ❌ **不要**开放 6379（Redis）
- ❌ **不要**开放 5001（Flask App）

### 3. 定期备份

```bash
# 设置每日自动备份
crontab -e

# 添加：每天凌晨 2 点备份
0 2 * * * cd /opt/testcase-agent && ./scripts/backup.sh
```

---

## ❓ 常见问题

### Q1: .env 文件会被推送到 GitHub 吗？
**A:** 不会！`.env` 已在 `.gitignore` 中，Git 会忽略它。

### Q2: 云服务器上的数据库能连上吗？
**A:** 能！所有服务在同一个 Docker 网络中，使用容器名互相访问。

### Q3: 如果重新部署，数据会丢失吗？
**A:** 不会！数据存储在 Docker volumes 中，重启容器不会影响数据。

### Q4: 如何查看数据库数据？
```bash
# 进入 PostgreSQL 容器
docker compose exec postgres psql -U testcase testcase_agent

# 查看所有表
\dt

# 查询数据
SELECT * FROM kb_docs LIMIT 10;
```

### Q5: 如何查看 Redis 数据？
```bash
# 进入 Redis 容器
docker compose exec redis redis-cli -a 你的Redis密码

# 查看所有 keys
KEYS *

# 查看缓存统计
INFO stats
```

### Q6: 端口冲突怎么办？
编辑 `docker-compose.yml`，修改端口映射：
```yaml
ports:
  - "8080:80"  # 将 Nginx 映射到 8080 端口
```

---

## 📞 技术支持

遇到问题？

1. 查看日志：`./scripts/logs.sh -f`
2. 检查服务：`docker compose ps`
3. 查看完整文档：`DEPLOYMENT.md`
4. 联系开发团队

---

**祝部署顺利！** 🚀
