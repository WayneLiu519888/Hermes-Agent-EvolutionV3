#!/bin/bash
# HermesAgentEvolution 安装脚本

set -e

echo "========================================="
echo "安装 HermesAgentEvolution 自我进化系统"
echo "========================================="

# 检查Python版本
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python版本: $PYTHON_VERSION"

if [[ $(echo "$PYTHON_VERSION < 3.10" | bc) -eq 1 ]]; then
    echo "错误: 需要 Python 3.10 或更高版本"
    exit 1
fi

# 创建虚拟环境
echo "创建虚拟环境..."
python3 -m venv venv

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 升级pip
echo "升级pip..."
pip install --upgrade pip

# 安装依赖
echo "安装依赖..."
pip install -r requirements-minimal.txt

# 创建必要的目录
echo "创建项目目录..."
mkdir -p logs data/evolution

# 设置环境变量（可选）
if [ ! -f .env ]; then
    echo "创建.env文件..."
    cat > .env << EOF
# HermesAgentEvolution 环境变量
FEISHU_WEBHOOK_URL=你的飞书webhook地址

# 日志配置
LOG_LEVEL=INFO

# 数据库配置
DB_PATH=./data/evolution.db
EOF
    echo "请编辑 .env 文件设置飞书webhook地址"
fi

# 测试安装
echo "测试安装..."
python3 -c "import numpy; import sqlalchemy; import requests; import yaml; print('✓ 所有依赖安装成功')"

# 创建启动脚本
echo "创建启动脚本..."
cat > start_evolution.sh << 'EOF'
#!/bin/bash
source venv/bin/activate
python main.py "$@"
EOF

chmod +x start_evolution.sh

echo ""
echo "========================================="
echo "安装完成！"
echo "========================================="
echo ""
echo "下一步:"
echo "1. 编辑 .env 文件设置飞书webhook地址"
echo "2. 运行 ./start_evolution.sh 启动系统"
echo "3. 运行 ./start_evolution.sh --continuous 启动持续进化"
echo ""
echo "项目结构:"
echo "  main.py              - 主程序"
echo "  src/                 - 源代码"
echo "  config/              - 配置文件"
echo "  data/evolution/      - 数据存储"
echo "  logs/                - 日志文件"
echo "  requirements*.txt    - 依赖文件"
echo ""
echo "开始你的进化之旅吧！🚀"