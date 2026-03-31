# Pixel Service - 后端服务启动指南

## 🎯 项目概览

**Pixel Service** 是一个 AI 内容生成平台的后端服务，主要功能包括：
- 用户认证（本地注册 + 微信/Google OAuth）
- AI 图像/视频生成（文生图、图生视频等）
- 积分消耗和会员管理
- 作品上传、存储、展示

**技术栈**：
- **框架**：FastAPI（异步 Python Web 框架）
- **任务队列**：Celery（分布式任务处理）
- **消息队列**：Redis（消息、缓存、锁）
- **数据库**：PostgreSQL（关系型数据存储）
- **存储**：Cloudflare R2（对象存储）

---

## 📋 前置准备（必需）

### 1. 环境要求

- **Python 3.11+**（推荐 3.12）
- **macOS / Linux / WSL2（Windows 推荐用 WSL2）**
- **Docker（可选，用于快速启动 PostgreSQL / Redis）**

### 2. 安装依赖

#### 方式 A：用本地 PostgreSQL + Redis（推荐快速尝试）

```bash
# 进入 service 目录
cd service

# 创建虚拟环境
python3.12 -m venv venv
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate  # Windows

# 安装 Python 依赖
pip install -r requirements.txt

# 安装 PostgreSQL 和 Redis（macOS 为例）
brew install postgresql@16 redis

# 启动 PostgreSQL 和 Redis
brew services start postgresql@16
brew services start redis
```

#### 方式 B：用 Docker（推荐生产环境）

```bash
# 使用 Docker Compose 启动 PostgreSQL 和 Redis
docker-compose up -d

# 然后安装 Python 依赖
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. 环境配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env，根据你的本地环境填写
# 主要填写以下项：
# - DATABASE_URL: 数据库连接字符串（本地：postgresql://user:password@localhost/pixel_db）
# - REDIS_URL: Redis 连接字符串（本地：redis://localhost:6379/0）
# - SECRET_KEY: JWT 签名密钥（随意填写测试值）
# - 其他 API Key（如有真实需求）
```

**示例 `.env` 本地配置**：

```env
# 数据库
DATABASE_URL=postgresql://postgres:password@localhost:5432/pixel_db
REDIS_URL=redis://localhost:6379/0

# JWT 密钥（开发环境随意，生产环境用强随机值）
SECRET_KEY=your-super-secret-key-for-dev

# 微信 OAuth（可先留空）
WECHAT_APP_ID=
WECHAT_APP_SECRET=
WECHAT_REDIRECT_URI=http://localhost:3000/auth/wechat/callback

# Google OAuth（可先留空）
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:3000/auth/google/callback

# 模型 API（可先留空）
TONGYI_API_KEY=
OPENAI_API_KEY=

# Cloudflare R2（可先留空）
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=

# 支付（可先留空）
WECHAT_PAY_MERCHANT_ID=
STRIPE_SECRET_KEY=

# 环境
ENVIRONMENT=development
LOG_LEVEL=INFO
```

---

## 🚀 启动步骤

### 步骤 1：初始化数据库

```bash
# 进入虚拟环境
source venv/bin/activate

# 方式 A：用 init.sql 快速初始化（推荐快速尝试）
psql -U postgres -h localhost < app/db/init.sql

# 方式 B：用 Alembic 数据库迁移（推荐生产环境）
alembic upgrade head
```

**创建数据库的补充说明**：

```bash
# 如果上面的命令报错"数据库不存在"，先创建数据库
psql -U postgres -h localhost -c "CREATE DATABASE pixel_db;"

# 然后再执行初始化
psql -U postgres -h localhost pixel_db < app/db/init.sql
```

### 步骤 2：启动 FastAPI 开发服务器

```bash
# 虚拟环境已激活的状态下
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**输出如下表示成功**：

```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

打开浏览器访问：

- **Swagger UI（API 文档）**：http://localhost:8000/docs
- **ReDoc（另一个 API 文档格式）**：http://localhost:8000/redoc
- **健康检查**：http://localhost:8000/api/v1/health

### 步骤 3：启动 Celery Worker（任务处理）

**新开一个终端**，在同一目录下：

```bash
# 激活虚拟环境
source venv/bin/activate

# 启动 Worker（监听 image 队列）
celery -A app.core.task_queue.celery_app worker --queues image -l info -c 2
```

**输出如下表示成功**：

```
 -------------- celery@YOUR-MACHINE v5.3.x ----------
 ---- **** -----
 --- * ***  * -- macOS-13.x ...
 -- * - **** ---
 - ** - *** ---
 - ** - *** ---
 - ** - *** ---
 - ** - *** ---
\  - ** - *** ---
 -------------- [queues]
              .> image ...
 
 [Tasks]
 . app.core.task_queue.tasks.image_tasks.generate_image
 
[*] Ready to accept tasks!
```

### 步骤 4（可选）：启动 Redis 监视器

如果你想看 Redis 的实时操作（仅用于调试），新开一个终端：

```bash
redis-cli monitor
```

---

## 🧪 快速测试

### 测试 1：健康检查

```bash
curl http://localhost:8000/api/v1/health
```

**预期返回**：

```json
{
  "status": "ok",
  "timestamp": "2026-03-31T16:30:00Z",
  "version": "1.0.0"
}
```

### 测试 2：用户注册

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "securepass123",
    "first_name": "Test",
    "last_name": "User"
  }'
```

**预期返回**：

```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "test@example.com",
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 7200
}
```

### 测试 3：获取用户信息

```bash
# 用上面返回的 access_token
curl http://localhost:8000/api/v1/account/profile \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 测试 4：提交生成任务

```bash
curl -X POST http://localhost:8000/api/v1/generation/submit \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "tool_id": "character-art",
    "prompt": "a fantasy elf character, detailed, epic",
    "num_images": 1
  }'
```

---

## 📖 API 文档位置

启动服务后，你可以在这些地方找到完整的 API 文档：

| 位置 | URL | 说明 |
|------|-----|------|
| **Swagger UI** | http://localhost:8000/docs | 交互式 API 测试 |
| **ReDoc** | http://localhost:8000/redoc | 美观的 API 文档 |
| **OpenAPI JSON** | http://localhost:8000/openapi.json | 原始 OpenAPI 规范 |

---

## 🔧 常见问题排查

### Q1: 连接数据库时出现 "could not connect to server"

**原因**：PostgreSQL 没启动或连接字符串错误

**解决**：

```bash
# 检查 PostgreSQL 是否运行
brew services list | grep postgresql

# 手动启动
brew services start postgresql@16

# 检查连接字符串（.env 中的 DATABASE_URL）
# 应该类似：postgresql://postgres:password@localhost:5432/pixel_db
```

### Q2: Celery Worker 启动失败

**原因**：可能是 Redis 没启动或虚拟环境中缺少依赖

**解决**：

```bash
# 确保 Redis 运行
brew services list | grep redis

# 或手动启动
redis-server

# 重新安装依赖
pip install -r requirements.txt --force-reinstall
```

### Q3: 导入错误 "No module named 'app'"

**原因**：虚拟环境没激活或没有安装依赖

**解决**：

```bash
# 激活虚拟环境
source venv/bin/activate

# 检查 pip 版本
pip --version

# 重新安装
pip install -r requirements.txt
```

### Q4: 端口 8000 已被占用

**原因**：另一个服务在用同一个端口

**解决**：

```bash
# 改用其他端口
uvicorn app.main:app --reload --port 8001

# 或关闭占用端口的进程
lsof -i :8000
kill -9 <PID>
```

### Q5: JWT 验证失败

**原因**：`SECRET_KEY` 在 `.env` 中没配置或不一致

**解决**：

```bash
# 确保 .env 中有 SECRET_KEY
cat .env | grep SECRET_KEY

# 如果没有，编辑 .env 添加
echo "SECRET_KEY=dev-secret-key-12345" >> .env
```

---

## 📁 项目结构概览

```
service/
├── app/
│   ├── main.py                  # FastAPI 应用入口
│   ├── config.py                # 配置管理
│   ├── api/v1/                  # API 路由
│   │   ├── auth.py              # 认证接口（注册、登录、OAuth）
│   │   ├── generation.py        # 生成任务接口
│   │   ├── account.py           # 账户接口（个人资料、积分）
│   │   ├── gallery.py           # 作品广场接口
│   │   ├── webhooks.py          # 支付回调
│   │   └── health.py            # 健康检查
│   ├── services/                # 业务逻辑层
│   │   ├── auth_service.py      # 认证业务
│   │   ├── generation_service.py # 生成任务业务
│   │   └── points_service.py    # 积分业务
│   ├── core/                    # 基础设施层
│   │   ├── auth/                # 认证（JWT、OAuth）
│   │   ├── cache/               # 缓存（Redis 连接、限流）
│   │   ├── model_gateway/       # 模型网关（路由、适配器）
│   │   ├── task_queue/          # Celery 任务队列
│   │   ├── storage/             # 存储（R2、图片处理）
│   │   └── monitoring/          # 监控（日志、指标）
│   ├── models/                  # 数据模型（SQLAlchemy ORM）
│   ├── schemas/                 # 请求/响应数据格式
│   ├── db/                      # 数据库
│   │   ├── database.py          # 连接和 Session
│   │   ├── init.sql             # 初始化 SQL
│   │   └── migrations/          # Alembic 数据库迁移
│   └── utils/                   # 工具函数
├── worker/
│   └── main.py                  # Celery Worker 入口
├── tests/                       # 测试
├── requirements.txt             # Python 依赖
├── .env.example                 # 环境变量模板
├── Dockerfile                   # Docker 镜像
├── alembic.ini                  # 数据库迁移配置
└── README.md                    # 本文档
```

---

## 🚀 生产部署（快速参考）

如果你想部署到云上（如 AWS / 阿里云），快速步骤：

```bash
# 1. 构建 Docker 镜像
docker build -t pixel-service:latest .

# 2. 推送到镜像仓库（如 Docker Hub）
docker push yourname/pixel-service:latest

# 3. 在云平台部署（以 Docker 为例）
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql://..." \
  -e REDIS_URL="redis://..." \
  -e SECRET_KEY="..." \
  yourname/pixel-service:latest

# 4. 启动 Celery Worker（在另一个容器或机器上）
docker run -d \
  -e DATABASE_URL="postgresql://..." \
  -e REDIS_URL="redis://..." \
  yourname/pixel-service:latest \
  celery -A app.core.task_queue.celery_app worker --queues image -l info
```

---

## 📞 需要帮助？

如果你遇到问题：

1. **查看日志**：启动时的输出信息通常会告诉你问题在哪
2. **检查 .env**：确保所有必需的环境变量都设置了
3. **测试连接**：用 `psql` 和 `redis-cli` 手动测试数据库和 Redis 连接
4. **重启服务**：有时候简单的重启能解决问题

---

## 快速命令参考

```bash
# 环境设置
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 启动各个服务
uvicorn app.main:app --reload  # FastAPI 服务器
celery -A app.core.task_queue.celery_app worker --queues image  # Celery Worker
redis-server  # Redis（如果不用 Docker）

# 数据库初始化
psql -U postgres -h localhost < app/db/init.sql
alembic upgrade head  # 用 Alembic 迁移

# 测试
curl http://localhost:8000/api/v1/health  # 健康检查
pytest tests/  # 运行单元测试

# 日志查看
tail -f app.log  # 查看应用日志
```

---

**祝你部署顺利！🎉**
