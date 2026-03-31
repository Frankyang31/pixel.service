#!/bin/bash

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
  echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
  echo -e "${GREEN}✅ $1${NC}"
}

log_error() {
  echo -e "${RED}❌ $1${NC}"
}

log_warn() {
  echo -e "${YELLOW}⚠️  $1${NC}"
}

# ============================================================================
# 第 0 步：环境检查
# ============================================================================

log_info "开始检查部署环境..."

# 检查是否为 root 或有 sudo 权限
if [ "$EUID" -ne 0 ]; then 
  log_error "此脚本需要 root 权限或 sudo 权限"
  echo "请使用: sudo ./deploy-prod.sh"
  exit 1
fi

# 检查 Docker
if ! command -v docker &> /dev/null; then
  log_warn "Docker 未安装，正在安装..."
  curl -fsSL https://get.docker.com -o get-docker.sh
  sh get-docker.sh
  usermod -aG docker ubuntu 2>/dev/null || true
  log_success "Docker 安装完成"
else
  log_success "Docker 已安装: $(docker --version)"
fi

# 检查 Docker Compose
if ! command -v docker-compose &> /dev/null; then
  log_warn "Docker Compose 未安装，正在安装..."
  curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
  chmod +x /usr/local/bin/docker-compose
  log_success "Docker Compose 安装完成"
else
  log_success "Docker Compose 已安装: $(docker-compose --version)"
fi

# 检查 Git
if ! command -v git &> /dev/null; then
  log_warn "Git 未安装，正在安装..."
  apt-get update && apt-get install -y git
  log_success "Git 安装完成"
else
  log_success "Git 已安装: $(git --version)"
fi

log_success "环境检查完成\n"

# ============================================================================
# 第 1 步：克隆/更新代码
# ============================================================================

log_info "准备代码仓库..."

DEPLOY_DIR="/opt/pixel"
SERVICE_DIR="$DEPLOY_DIR/service"

# 创建部署目录
mkdir -p "$DEPLOY_DIR"
cd "$DEPLOY_DIR"

# 如果已存在 monorepo 则更新，否则克隆
if [ -d ".git" ]; then
  log_info "更新现有代码仓库..."
  git pull origin main
else
  log_info "克隆 monorepo..."
  git clone --recurse-submodules https://github.com/Frankyang31/pixel.monorepo.git .
fi

cd "$SERVICE_DIR"
log_success "代码已准备好: $SERVICE_DIR\n"

# ============================================================================
# 第 2 步：准备环境变量
# ============================================================================

log_info "准备环境配置..."

if [ ! -f ".env.production" ]; then
  log_warn ".env.production 不存在，复制示例文件..."
  cp .env.production.example .env.production
  log_warn "请编辑 .env.production 并填入正确的敏感信息（数据库密码、API 密钥等）"
  echo "编辑命令: nano $SERVICE_DIR/.env.production"
  exit 1
fi

log_success "环境配置已准备\n"

# ============================================================================
# 第 3 步：创建必要的目录和文件
# ============================================================================

log_info "创建必要的目录结构..."

mkdir -p "$DEPLOY_DIR/nginx/conf.d"
mkdir -p "$DEPLOY_DIR/nginx/ssl"
mkdir -p "$DEPLOY_DIR/logs"

log_success "目录结构已创建\n"

# ============================================================================
# 第 4 步：启动容器
# ============================================================================

log_info "启动 Docker 容器..."

# 使用生产级 docker-compose 配置
docker-compose -f docker-compose.prod.yml up -d

# 等待容器启动
sleep 10

log_success "容器已启动\n"

# ============================================================================
# 第 5 步：运行数据库迁移
# ============================================================================

log_info "运行数据库迁移..."

docker-compose -f docker-compose.prod.yml exec -T api alembic upgrade head

log_success "数据库迁移完成\n"

# ============================================================================
# 第 6 步：验证健康状态
# ============================================================================

log_info "验证服务健康状态..."

# 等待 FastAPI 启动
for i in {1..30}; do
  if docker exec pixel_api curl -s http://localhost:8000/health > /dev/null 2>&1; then
    log_success "FastAPI 已启动并响应健康检查"
    break
  fi
  echo -n "."
  sleep 1
done

echo ""

# 检查所有容器状态
log_info "容器状态:"
docker-compose -f docker-compose.prod.yml ps

log_success "部署完成！\n"

# ============================================================================
# 第 7 步：显示后续步骤
# ============================================================================

log_info "后续步骤:"
echo ""
echo "1. 访问 API: http://118.25.22.37:8000/docs"
echo ""
echo "2. 查看日志:"
echo "   docker-compose -f docker-compose.prod.yml logs -f api"
echo ""
echo "3. 进入容器 shell:"
echo "   docker-compose -f docker-compose.prod.yml exec api bash"
echo ""
echo "4. 停止服务:"
echo "   docker-compose -f docker-compose.prod.yml down"
echo ""
echo "5. 查看更多命令:"
echo "   cat $SERVICE_DIR/DEPLOYMENT.md"
echo ""

log_success "部署脚本执行完成！"
