#!/bin/bash

# 阿里云服务器一键部署脚本
# 服务器IP: 47.114.100.171

echo "🚀 开始部署测试用例生成器到阿里云..."
echo "================================================"

# 服务器信息
SERVER_IP="47.114.100.171"
SERVER_USER="root"
PROJECT_NAME="testcase-agent"
REMOTE_DIR="/var/www/${PROJECT_NAME}"

echo "📋 部署信息:"
echo "   服务器IP: ${SERVER_IP}"
echo "   部署目录: ${REMOTE_DIR}"
echo ""

# 依赖检查
if ! command -v rsync >/dev/null 2>&1; then
    echo "❌ 本地缺少 rsync，请先安装 (macOS: brew install rsync)"
    exit 1
fi

if [ ! -f "requirements.txt" ]; then
    echo "❌ 未找到 requirements.txt，无法继续部署"
    exit 1
fi

echo ""

# 提示用户
echo "⚠️  请确保："
echo "   1. 已设置服务器 root 密码"
echo "   2. 安全组已开放 22/80/443 端口"
echo ""
read -p "按 Enter 继续，或 Ctrl+C 取消..."

# 第一步：上传项目文件
echo ""
echo "📤 步骤 1/5: 同步项目文件到服务器..."
ssh ${SERVER_USER}@${SERVER_IP} "mkdir -p ${REMOTE_DIR}"

EXCLUDES=(
    "--exclude=.git"
    "--exclude=.gitignore"
    "--exclude=__pycache__"
    "--exclude=.venv"
    "--exclude=venv"
    "--exclude=*.pyc"
    "--exclude=run.log"
)

rsync -av --delete "${EXCLUDES[@]}" ./ "${SERVER_USER}@${SERVER_IP}:${REMOTE_DIR}/"

echo "✅ 项目文件同步完成"

# 第二步：安装系统依赖
echo ""
echo "📦 步骤 2/5: 安装系统依赖..."
ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
    # 更新系统
    echo "正在更新系统包..."
    export DEBIAN_FRONTEND=noninteractive
    apt update -y
    
    # 安装 Python 和工具
    echo "正在安装 Python 3.9..."
    apt install -y python3.9 python3.9-venv python3-pip
    
    # 安装 Nginx
    echo "正在安装 Nginx..."
    apt install -y nginx
    
    # 安装 Supervisor
    echo "正在安装 Supervisor..."
    apt install -y supervisor
    
    echo "✅ 系统依赖安装完成"
ENDSSH

# 第三步：配置 Python 环境
echo ""
echo "🐍 步骤 3/5: 配置 Python 虚拟环境..."
ssh ${SERVER_USER}@${SERVER_IP} << ENDSSH
    cd ${REMOTE_DIR}
    
    # 创建虚拟环境
    echo "创建虚拟环境..."
    python3.9 -m venv venv
    
    # 激活并安装依赖
    echo "安装 Python 依赖..."
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # 添加执行权限
    chmod +x start_production.sh
    
    echo "✅ Python 环境配置完成"
ENDSSH

# 第四步：配置 Supervisor
echo ""
echo "⚙️  步骤 4/5: 配置进程守护..."
ssh ${SERVER_USER}@${SERVER_IP} << ENDSSH
    # 创建 Supervisor 配置
    cat > /etc/supervisor/conf.d/testcase-agent.conf << EOF
[program:testcase-agent]
directory=${REMOTE_DIR}
command=${REMOTE_DIR}/venv/bin/gunicorn -w 2 -b 127.0.0.1:5001 --timeout 180 app:app
user=root
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/testcase-agent.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=10
EOF

    # 重新加载 Supervisor
    supervisorctl reread
    supervisorctl update
    supervisorctl start testcase-agent
    
    echo "✅ 进程守护配置完成"
ENDSSH

# 第五步：配置 Nginx
echo ""
echo "🌐 步骤 5/5: 配置 Nginx 反向代理..."
ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
    # 创建 Nginx 配置
    cat > /etc/nginx/sites-available/testcase-agent << EOF
server {
    listen 80;
    server_name _;  # 接受所有域名/IP 访问

    access_log /var/log/nginx/testcase-agent-access.log;
    error_log /var/log/nginx/testcase-agent-error.log;

    # 反向代理到 Flask 应用
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置
        proxy_connect_timeout 180;
        proxy_send_timeout 180;
        proxy_read_timeout 180;
    }

    # 静态文件缓存
    location ~* \.(css|js|jpg|jpeg|png|gif|ico)$ {
        expires 7d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

    # 启用站点
    ln -sf /etc/nginx/sites-available/testcase-agent /etc/nginx/sites-enabled/
    
    # 删除默认站点
    rm -f /etc/nginx/sites-enabled/default
    
    # 测试配置
    nginx -t
    
    # 重启 Nginx
    systemctl restart nginx
    
    echo "✅ Nginx 配置完成"
ENDSSH

# 完成
echo ""
echo "================================================"
echo "🎉 部署完成！"
echo "================================================"
echo ""
echo "📱 访问地址："
echo "   http://47.114.100.171"
echo ""
echo "📊 管理命令："
echo "   查看状态: ssh root@${SERVER_IP} 'supervisorctl status'"
echo "   查看日志: ssh root@${SERVER_IP} 'tail -f /var/log/testcase-agent.log'"
echo "   重启服务: ssh root@${SERVER_IP} 'supervisorctl restart testcase-agent'"
echo ""
echo "💡 提示："
echo "   - 如果访问不了，检查安全组是否开放 80 端口"
echo "   - 可以用浏览器打开 http://47.114.100.171 测试"
echo ""
