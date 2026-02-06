#!/bin/bash

# 基金跟踪器 Oracle Cloud 部署脚本
# 使用方法: ./deploy-to-oracle-cloud.sh <服务器IP> <SSH密钥路径>

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查参数
if [ $# -lt 2 ]; then
    echo -e "${RED}用法: $0 <服务器IP> <SSH密钥路径>${NC}"
    echo "示例: $0 132.145.123.45 ~/.ssh/oracle-cloud.key"
    exit 1
fi

SERVER_IP=$1
SSH_KEY=$2
USER="ubuntu"
PROJECT_NAME="fundtracker"
REMOTE_DIR="~/${PROJECT_NAME}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  基金跟踪器 Oracle Cloud 部署脚本${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "服务器IP: ${YELLOW}$SERVER_IP${NC}"
echo -e "SSH密钥: ${YELLOW}$SSH_KEY${NC}"
echo ""

# 检查本地文件
echo -e "${GREEN}[1/6] 检查本地文件...${NC}"
if [ ! -f "$SSH_KEY" ]; then
    echo -e "${RED}错误: SSH密钥文件不存在: $SSH_KEY${NC}"
    exit 1
fi

if [ ! -d "../backend" ]; then
    echo -e "${RED}错误: 后端代码目录不存在${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 本地文件检查通过${NC}"

# 测试 SSH 连接
echo -e "${GREEN}[2/6] 测试 SSH 连接...${NC}"
if ! ssh -i "$SSH_KEY" -o ConnectTimeout=5 -o StrictHostKeyChecking=no "${USER}@${SERVER_IP}" "echo 'SSH连接成功'" > /dev/null 2>&1; then
    echo -e "${RED}错误: 无法连接到服务器，请检查IP和密钥${NC}"
    exit 1
fi
echo -e "${GREEN}✓ SSH 连接成功${NC}"

# 创建远程目录结构
echo -e "${GREEN}[3/6] 创建远程目录结构...${NC}"
ssh -i "$SSH_KEY" "${USER}@${SERVER_IP}" << EOF
    mkdir -p ${REMOTE_DIR}/backend
    echo "目录创建成功"
EOF

# 上传后端代码
echo -e "${GREEN}[4/6] 上传后端代码...${NC}"
scp -i "$SSH_KEY" -r ../backend/* "${USER}@${SERVER_IP}:${REMOTE_DIR}/backend/"
scp -i "$SSH_KEY" ../docker/docker-compose.prod.yml "${USER}@${SERVER_IP}:${REMOTE_DIR}/"
scp -i "$SSH_KEY" ../docker/.env.example "${USER}@${SERVER_IP}:${REMOTE_DIR}/.env"
echo -e "${GREEN}✓ 代码上传完成${NC}"

# 在服务器上部署
echo -e "${GREEN}[5/6] 在服务器上部署服务...${NC}"
ssh -i "$SSH_KEY" "${USER}@${SERVER_IP}" << 'REMOTE_SCRIPT'
    cd ~/fundtracker
    
    # 检查 Docker 是否安装
    if ! command -v docker &> /dev/null; then
        echo "安装 Docker..."
        sudo apt update
        sudo apt install -y docker.io docker-compose
        sudo systemctl start docker
        sudo systemctl enable docker
        sudo usermod -aG docker $USER
        echo "Docker 安装完成，请重新运行脚本"
        exit 1
    fi
    
    # 停止旧服务
    echo "停止旧服务..."
    docker-compose -f docker-compose.prod.yml down 2>/dev/null || true
    
    # 拉取最新镜像
    echo "拉取最新镜像..."
    docker-compose -f docker-compose.prod.yml pull
    
    # 构建并启动服务
    echo "构建并启动服务..."
    docker-compose -f docker-compose.prod.yml up -d --build
    
    # 等待服务启动
    echo "等待服务启动..."
    sleep 10
    
    # 检查服务状态
    echo "检查服务状态..."
    docker-compose -f docker-compose.prod.yml ps
    
    echo ""
    echo "部署完成！"
    echo "API 地址: http://$(curl -s ifconfig.me):8000"
REMOTE_SCRIPT

echo -e "${GREEN}✓ 服务部署完成${NC}"

# 测试 API
echo -e "${GREEN}[6/6] 测试 API 接口...${NC}"
sleep 5
API_URL="http://${SERVER_IP}:8000/api/v1/funds/realtime/000001"
echo "测试地址: $API_URL"

if curl -s --max-time 10 "$API_URL" > /dev/null; then
    echo -e "${GREEN}✓ API 测试成功${NC}"
else
    echo -e "${YELLOW}⚠ API 测试失败，服务可能还在启动中${NC}"
    echo "请等待 30 秒后手动测试: curl $API_URL"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "API 地址: ${YELLOW}http://${SERVER_IP}:8000${NC}"
echo -e "API 文档: ${YELLOW}http://${SERVER_IP}:8000/docs${NC}"
echo ""
echo "常用命令:"
echo "  查看日志: ssh -i $SSH_KEY ${USER}@${SERVER_IP} 'cd ~/fundtracker && docker-compose -f docker-compose.prod.yml logs -f'"
echo "  重启服务: ssh -i $SSH_KEY ${USER}@${SERVER_IP} 'cd ~/fundtracker && docker-compose -f docker-compose.prod.yml restart'"
echo "  停止服务: ssh -i $SSH_KEY ${USER}@${SERVER_IP} 'cd ~/fundtracker && docker-compose -f docker-compose.prod.yml down'"
echo ""
