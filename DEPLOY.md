# 阿里云服务器部署指南

## 📋 部署前准备

### 1. 服务器要求
- **系统**：Ubuntu 20.04/22.04 或 CentOS 7/8
- **配置**：**2核2G 即可**（低成本方案，月费约 50-80 元）
- **Python**：3.9 或以上
- **域名**：已备案的自定义域名（或使用阿里云提供的临时域名）

### 2. 本地准备
确保以下文件已配置：
- `.env`：包含 API Key 和模型配置
- `requirements.txt`：Python 依赖列表

---

## � 成本说明（2核2G 方案）

### 阿里云 ECS 轻量应用服务器
- **配置**：2核2G 3M带宽
- **价格**：约 **60-80 元/月**
- **流量**：1TB/月（个人使用足够）
- **推荐区域**：华北、华东（延迟低）

### 域名成本
- **新注册 .com 域名**：约 55-60 元/年
- **备案**：免费（阿里云协助，需要 7-20 天）
- **可选**：使用阿里云提供的临时域名（免费，无需备案）

### HTTPS 证书
- **Let's Encrypt**：完全免费
- **自动续期**：无需人工干预

### 总成本
- **首月**：服务器 60 元 + 域名 60 元 = **120 元**
- **次月起**：服务器 60 元/月
- **年成本**：约 **780 元**（含域名）

### 💡 省钱技巧
1. **新用户优惠**：阿里云新用户首年可享受 **5折优惠**，约 30-40 元/月
2. **长期购买**：一次购买 1-3 年，可享受 **7-8 折优惠**
3. **学生优惠**：学生认证后，2核2G 低至 **9.5 元/月**
4. **域名选择**：
   - `.top`、`.xyz` 域名首年约 **8-15 元**（比 .com 便宜）
   - 或使用阿里云临时域名（免费，但无法自定义）

### 📊 配置对比（帮你选择）

| 配置 | 价格 | 适用场景 | 性能表现 |
|------|------|---------|---------|
| **2核2G** ⭐ | 60元/月 | 个人使用、小团队（<10人） | 单次处理 10-20 张图片 PRD 正常 |
| 2核4G | 100元/月 | 中型团队（10-30人） | 单次处理 30-50 张图片 PRD |
| 4核8G | 200元/月 | 大型团队或高并发 | 单次处理 100+ 张图片 PRD |

**推荐**：个人使用或小团队选 **2核2G**，性价比最高！

---

## 🚀 快速部署步骤

### 第一步：连接服务器

```bash
ssh root@你的服务器IP
```

### 第二步：安装依赖

```bash
# 更新系统
apt update && apt upgrade -y  # Ubuntu/Debian
# yum update -y  # CentOS

# 安装 Python 3.9+
apt install python3.9 python3.9-venv python3-pip -y

# 安装 Nginx
apt install nginx -y

# 安装 Supervisor（进程守护）
apt install supervisor -y
```

### 第三步：部署应用

```bash
# 创建应用目录
mkdir -p /var/www/testcase-agent
cd /var/www/testcase-agent

# 上传项目文件（使用 scp 或 git）
# 方式1：从本地上传
# scp -r /Users/xujinliang/Desktop/Testcase\ Agent/* root@服务器IP:/var/www/testcase-agent/

# 方式2：从 GitHub 克隆
git clone https://github.com/JAMES1390825/Testcase-Agent.git .

# 创建虚拟环境
python3.9 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
pip install gunicorn  # 生产级 WSGI 服务器
```

### 第四步：配置环境变量

```bash
# 创建 .env 文件
nano .env
```

添加以下内容：
```env
OPENAI_API_KEY=sk-your-api-key
OPENAI_BASE_URL=https://api.sealos.io/v1
TEXT_MODEL_NAME=qwen-turbo
VISION_MODEL_NAME=qwen-vl-max
DISABLE_VISION=0
```

按 `Ctrl+X`，然后 `Y`，回车保存。

### 第五步：配置 Supervisor（进程守护）

```bash
nano /etc/supervisor/conf.d/testcase-agent.conf
```

添加以下内容（**2核2G 优化配置**）：
```ini
[program:testcase-agent]
directory=/var/www/testcase-agent
command=/var/www/testcase-agent/venv/bin/gunicorn -w 2 -b 127.0.0.1:5001 --timeout 180 app:app
user=root
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/testcase-agent.log
```

**配置说明（针对 2核2G）**：
- `-w 2`：2个工作进程（匹配 CPU 核心数）
- `--timeout 180`：180秒超时（处理大文档足够）
- 内存占用：约 300-500MB（系统剩余 1.5G 够用）

启动服务：
```bash
supervisorctl reread
supervisorctl update
supervisorctl start testcase-agent
supervisorctl status  # 检查状态
```

### 第六步：配置 Nginx 反向代理

```bash
nano /etc/nginx/sites-available/testcase-agent
```

添加以下配置：
```nginx
server {
    listen 80;
    server_name 你的域名.com;  # 替换为你的阿里云域名

    # 访问日志
    access_log /var/log/nginx/testcase-agent-access.log;
    error_log /var/log/nginx/testcase-agent-error.log;

    # 反向代理到 Flask 应用
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置（处理长时间请求）
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        proxy_read_timeout 300;
    }

    # 静态文件加速
    location ~* \.(css|js|jpg|jpeg|png|gif|ico)$ {
        expires 7d;
        add_header Cache-Control "public, immutable";
    }
}
```

启用站点并重启 Nginx：
```bash
ln -s /etc/nginx/sites-available/testcase-agent /etc/nginx/sites-enabled/
nginx -t  # 测试配置
systemctl restart nginx
```

### 第七步：配置域名解析

在阿里云域名控制台添加 A 记录：
- **记录类型**：A
- **主机记录**：@ 或 www
- **记录值**：你的服务器公网IP
- **TTL**：10分钟

---

## 🔒 配置 HTTPS（可选但推荐）

### 使用 Let's Encrypt 免费证书

```bash
# 安装 Certbot
apt install certbot python3-certbot-nginx -y

# 自动配置 HTTPS
certbot --nginx -d 你的域名.com

# 设置自动续期
certbot renew --dry-run
```

---

## 📊 管理命令

### 查看服务状态
```bash
supervisorctl status testcase-agent
```

### 重启服务
```bash
supervisorctl restart testcase-agent
```

### 查看日志
```bash
tail -f /var/log/testcase-agent.log
```

### 更新代码
```bash
cd /var/www/testcase-agent
git pull origin main
supervisorctl restart testcase-agent
```

---

## 🔧 性能优化

### 1. Gunicorn 工作进程数（2核2G 配置）
```bash
# 2核2G 服务器：2个工作进程
-w 2 --timeout 180

# 如果后续升级到 4核4G：
-w 4 --timeout 300
```

**注意**：进程数过多会导致内存不足，2核2G 建议最多 2-3 个进程。

### 2. 减少内存占用
在 `.env` 中添加：
```env
# 限制图片批处理大小（降低内存峰值）
MAX_IMAGES_PER_BATCH=5        # 默认 10，改为 5
IMAGE_MAX_SIZE=800             # 默认 1024，改为 800
MAX_SECTION_CHARS=40000        # 默认 60000，改为 40000
```

### 2. Nginx 缓存（可选）
在 Nginx 配置中添加：
```nginx
# 在 http 块中
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=my_cache:10m max_size=100m inactive=60m;
```

**注意**：2核2G 服务器建议缓存设置为 100MB（默认 1G 太大）

### 3. 防火墙设置
```bash
# 允许 HTTP/HTTPS
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

---

## 🐛 故障排查

### 服务无法启动
```bash
# 查看详细日志
journalctl -u supervisor -f
tail -f /var/log/testcase-agent.log
```

### 502 Bad Gateway
- 检查 Gunicorn 是否运行：`supervisorctl status`
- 检查端口占用：`netstat -tunlp | grep 5001`
- 检查防火墙：`ufw status`

### 域名无法访问
- 检查 DNS 解析：`nslookup 你的域名.com`
- 检查 Nginx 配置：`nginx -t`
- 检查端口监听：`netstat -tunlp | grep 80`

---

## 📞 访问你的应用

部署完成后，访问：
- **HTTP**：http://你的域名.com
- **HTTPS**（如已配置）：https://你的域名.com

---

## 🎯 下一步

- [ ] 配置 HTTPS 证书
- [ ] 设置定期备份
- [ ] 配置监控告警
- [ ] 优化数据库（如需要）
