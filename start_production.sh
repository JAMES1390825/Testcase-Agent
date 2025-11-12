#!/bin/bash

# 测试用例生成器 - 生产环境启动脚本
# 用于云服务器部署（阿里云、腾讯云等）

echo "🚀 启动测试用例生成器（生产模式）..."

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 未找到虚拟环境，请先创建："
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate

# 使用 Gunicorn 启动（生产级 WSGI 服务器）
# 2核2G 服务器优化配置：
# -w 2: 2个工作进程（匹配 CPU 核心数，避免内存不足）
# -b 0.0.0.0:5001: 绑定到所有网卡的 5001 端口
# --timeout 180: 请求超时时间 180 秒（处理大文档/多图片）
# --access-logfile -: 访问日志输出到标准输出
# --error-logfile -: 错误日志输出到标准输出

gunicorn -w 2 \
    -b 0.0.0.0:5001 \
    --timeout 180 \
    --access-logfile - \
    --error-logfile - \
    app:app

echo "✅ 服务已启动在 0.0.0.0:5001"
