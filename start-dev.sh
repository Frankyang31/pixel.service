#!/bin/bash
# 快速启动脚本 - 一键启动 Pixel Service 开发环境

set -e  # 任何命令失败都退出

# 定义颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_status() {
  echo -e "${BLUE}▶ $1${NC}"
}

print_success() {
  echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
  echo -e "${RED}✗ $1${NC}"
}

print_warning() {
  echo -e "${YELLOW}⚠ $1${NC}"
}

# 获取当前脚本目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

print_status "启动 Pixel Service 开发环境..."
echo ""

# 1. 检查虚拟环境
print_status "检查虚拟环境..."
if [ ! -d "$SCRIPT_DIR/venv" ]; then
  print_warning "虚拟环境不存在，正在创建..."
  python3.12 -m venv "$SCRIPT_DIR/venv"
  print_success "虚拟环境已创建"
else
  print_success "虚拟环境已存在"
fi

# 2. 激活虚拟环境
print_status "激活虚拟环境..."
source "$SCRIPT_DIR/venv/bin/activate"
print_success "虚拟环境已激活"

# 3. 检查依赖
print_status "检查 Python 依赖..."
if pip list | grep -q "fastapi"; then
  print_success "依赖已安装"
else
  print_warning "依赖不完整，正在安装..."
  pip install -q -r "$SCRIPT_DIR/requirements.txt"
  print_success "依赖已安装"
fi

# 4. 检查 .env 文件
print_status "检查环境配置..."
if [ ! -f "$SCRIPT_DIR/.env" ]; then
  print_warning ".env 文件不存在，正在复制模板..."
  cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
  print_warning "请编辑 .env 文件，填入你的本地数据库和 Redis 连接信息"
  print_warning "默认本地数据库配置："
  print_warning "  DATABASE_URL=postgresql://postgres:password@localhost:5432/pixel_db"
  print_warning "  REDIS_URL=redis://localhost:6379/0"
  echo ""
fi

# 5. 检查数据库
print_status "检查数据库连接..."
source "$SCRIPT_DIR/.env" 2>/dev/null || true

# 简单检查（不实际连接，避免等待超时）
if [ -z "$DATABASE_URL" ]; then
  print_error "DATABASE_URL 未设置！请编辑 .env 文件"
  exit 1
fi
print_success "环境配置有效"

# 6. 检查 Redis
print_status "检查 Redis..."
if ! command -v redis-cli &> /dev/null; then
  print_warning "redis-cli 未找到，假设 Redis 已通过其他方式启动"
else
  if redis-cli ping &> /dev/null; then
    print_success "Redis 已连接"
  else
    print_warning "Redis 连接失败，请确保 Redis 已启动"
    print_warning "  brew services start redis  # macOS"
    print_warning "  或"
    print_warning "  redis-server  # 手动启动"
  fi
fi

# 7. 启动服务
echo ""
print_success "所有检查通过！"
echo ""
print_status "启动 FastAPI 服务器..."
print_warning "提示：按 Ctrl+C 停止服务"
echo ""

# 在同一进程启动 FastAPI
cd "$SCRIPT_DIR"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 下面的代码不会执行到（FastAPI 占用当前进程），但为了完整性保留
echo ""
print_success "服务已停止"
