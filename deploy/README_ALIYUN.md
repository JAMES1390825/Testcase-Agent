阿里云 ECS 部署指南（Ubuntu/CentOS 通用）

本文档指导你把本项目部署到公网服务器（如 47.114.100.171）。提供两种方案：原生部署（Gunicorn+Nginx）与 Docker 部署。推荐优先原生部署，简单稳定。

一、准备工作

1) 安全组放行
- 开放 80/443（HTTP/HTTPS）。
- 关闭 5001 的对外访问（仅本机回环使用）。

2) 系统依赖
- Python 3.9+（推荐 3.11）
- Git、Nginx、systemd（大多数发行版自带）

二、原生部署（Gunicorn + Nginx，推荐）

1) 拉取代码与安装依赖
```
sudo mkdir -p /opt/testcase-agent && sudo chown -R $USER:$USER /opt/testcase-agent
cd /opt/testcase-agent
git clone https://github.com/JAMES1390825/Testcase-Agent .

# 建议使用虚拟环境
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

2) 创建并启动 systemd 服务
```
sudo cp deploy/systemd/testcase-agent.service /etc/systemd/system/testcase-agent.service

# 如需调整：
# - WorkingDirectory 改为你的实际路径
# - ExecStart 中 workers/threads/端口可按机器配置修改
# - Environment 可设置限流并发等环境变量

sudo systemctl daemon-reload
sudo systemctl enable testcase-agent
sudo systemctl start testcase-agent
sudo systemctl status testcase-agent --no-pager
```

默认监听 127.0.0.1:5001，供 Nginx 反向代理。

3) 配置 Nginx 反向代理
```
sudo cp deploy/nginx/testcase-agent.conf /etc/nginx/conf.d/testcase-agent.conf
# 可把 server_name 改为你的域名或公网 IP
sudo nginx -t
sudo systemctl reload nginx
```

访问 http://你的IP/ 即可打开前端；/api/* 由 Nginx 转发到本机 5001。

4) 可选：签发 HTTPS 证书
```
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your.domain.com
```

三、运行参数与性能建议

环境变量（在 systemd 的 Environment 中设置）：
- MAX_CONCURRENT_MODEL_CALLS：全局模型最大并发调用（默认 3；小机建议 2）
- MIN_CALL_INTERVAL_MS：模型调用最小间隔毫秒（默认 0；遇 429 可设 50–100）

前端“视觉参数”可调：
- 批次并发数：建议 2–4（2C2G 建议 2）
- 图片下载并发数：建议 4–8（2C2G 建议 3–4）
- 图片压缩尺寸：640–768（降低 CPU/内存占用）
- JPEG 质量：65–75（降低带宽）

四、Docker 部署（可选）

1) 构建并运行容器
```
docker build -t testcase-agent:latest .
docker run -d --name testcase-agent \
  -p 5001:5001 \
  -e MAX_CONCURRENT_MODEL_CALLS=2 \
  -e MIN_CALL_INTERVAL_MS=0 \
  testcase-agent:latest
```
然后用 Nginx 反代 127.0.0.1:5001 即可；或直接开放 5001（不推荐）。

五、常用排错
- systemctl status testcase-agent 查看运行状态
- journalctl -u testcase-agent -f 实时日志
- nginx -t && systemctl reload nginx 重载 Nginx
- 检查安全组与防火墙端口（80/443）
- 500 报错：查看后端日志；若为“CSV 不规范”，我们已默认宽松模式自动修复/放行

六、目录说明
- /opt/testcase-agent：代码根目录（包含 index.html、script.js、style.css 和后端）
- deploy/systemd/testcase-agent.service：systemd 服务模板
- deploy/nginx/testcase-agent.conf：Nginx 站点模板（根目录直接提供前端静态文件，/api/* 反向代理）

完成后你可以把服务器 IP 或域名发我，我再远程核验首页/接口是否都正常。
