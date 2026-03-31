# 🚀 Pixel Service - 三步快速启动

> 给后端小白的最简化启动指南

## 🎯 目标

启动一个本地开发环境，能在浏览器访问 API 文档并测试接口。

---

## 💻 三个步骤

### 第 1 步：准备环境（第一次做，后续不需要重复）

#### 1a. 安装依赖软件（只做一次）

**macOS 用户**：

```bash
# 安装 PostgreSQL 和 Redis
brew install postgresql@16 redis

# 启动数据库和缓存
brew services start postgresql@16
brew services start redis
```

**Windows 用户（WSL2）**：

```bash
# WSL2 中执行相同的 macOS 命令
brew install postgresql@16 redis
brew services start postgresql@16
brew services start redis
```

**Linux 用户**：

```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib redis-server
sudo systemctl start postgresql
sudo systemctl start redis-server
```

**或用 Docker（推荐，无需装 PostgreSQL/Redis）**：

```bash
# 确保装了 Docker Desktop，然后在项目根目录运行：
docker-compose up -d

# 这会自动启动 PostgreSQL 和 Redis
# 验证：docker ps
```

#### 1b. 创建虚拟环境（只做一次）

```bash
# 进入 service 目录
cd service

# 创建虚拟环境
python3.12 -m venv venv

# 激活虚拟环境
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate  # Windows
```

#### 1c. 安装 Python 包（只做一次）

```bash
pip install -r requirements.txt
```

#### 1d. 配置环境变量（只做一次）

```bash
# 复制配置模板
cp .env.example .env

# 打开 .env，填写本地数据库信息
# 如果用了上面的本地 PostgreSQL + Redis，无需改动，保持默认即可
```

---

### 第 2 步：初始化数据库（第一次做，后续不需要重复）

```bash
# 在虚拟环境中
source venv/bin/activate

# 方法 A：用 SQL 脚本初始化（快速）
psql -U postgres -h localhost < app/db/init.sql

# 如果报错 "database pixel_db does not exist"，先创建数据库：
psql -U postgres -h localhost -c "CREATE DATABASE pixel_db;"

# 然后再执行初始化
psql -U postgres -h localhost pixel_db < app/db/init.sql
```

**验证初始化成功**：

```bash
# 连接数据库查看表
psql -U postgres -h localhost pixel_db -c "\dt"
```

应该看到类似输出（9 张表）：

```
             表名单             
          架构          |     名称      | 类型  |   所有者
-----------+---------+-------+----------
 public    | assets  | 表    | postgres
 public    | points_account    | 表    | postgres
 ... (其他表)
```

---

### 第 3 步：启动服务（每次开发都要做）

#### 方法 A：用快速启动脚本（最简单）

```bash
# 在 service 目录
./start-dev.sh

# 会自动检查环境、依赖，然后启动 FastAPI 服务器
```

#### 方法 B：手动启动（推荐理解原理）

**Terminal 1 - 启动 FastAPI 服务器**：

```bash
cd service
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

看到这个输出表示成功：

```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

**Terminal 2 - 启动 Celery Worker（处理后台任务）**：

```bash
cd service
source venv/bin/activate
celery -A app.core.task_queue.celery_app worker --queues image -l info -c 2
```

看到这个输出表示成功：

```
[*] Ready to accept tasks!
```

---

## ✅ 验证启动成功

### 打开浏览器访问

- **API 文档（Swagger UI）**：http://localhost:8000/docs
- **另一个 API 文档格式（ReDoc）**：http://localhost:8000/redoc

**看到交互式 API 文档说明启动成功！🎉**

### 快速测试接口

```bash
# 健康检查
curl http://localhost:8000/api/v1/health

# 预期返回
# {"status":"ok","timestamp":"...","version":"1.0.0"}
```

---

## 🛑 停止服务

**按 Ctrl+C** 停止 FastAPI 服务器

如果用了 Docker：

```bash
docker-compose down
```

---

## 🆘 常见问题

### ❓ "connection refused"（无法连接数据库）

**原因**：PostgreSQL 没启动

**解决**：

```bash
# 检查是否启动
brew services list | grep postgresql

# 手动启动
brew services start postgresql@16

# 或用 Docker
docker-compose up -d
```

### ❓ "python3.12: command not found"

**原因**：没装 Python 3.12

**解决**：

```bash
# 用其他版本也可以（3.11+ 都行）
python3.11 -m venv venv

# 或安装 3.12
brew install python@3.12
```

### ❓ 虚拟环境激活失败

**原因**：路径错误或文件损坏

**解决**：

```bash
# 删除旧的虚拟环境
rm -rf venv

# 重新创建
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### ❓ "ModuleNotFoundError: No module named 'app'"

**原因**：虚拟环境没激活或依赖没装

**解决**：

```bash
# 确保激活虚拟环境
source venv/bin/activate

# 检查依赖
pip list | grep fastapi

# 如果没有，重新装
pip install -r requirements.txt
```

---

## 📝 下一步

启动成功后，你可以：

1. **在 Swagger UI（http://localhost:8000/docs）中测试接口**
   - 点击"Try it out"按钮
   - 填入参数
   - 点击"Execute"查看结果

2. **阅读完整的启动文档**：`README.md`

3. **查看项目结构**：`service/` 目录下

4. **开始开发**：修改代码，自动热重载（uvicorn 已启用 `--reload`）

---

## 🎓 学习资源

- **FastAPI 官方文档**：https://fastapi.tiangolo.com/
- **Celery 官方文档**：https://docs.celeryproject.io/
- **PostgreSQL 官方文档**：https://www.postgresql.org/docs/
- **Redis 官方文档**：https://redis.io/documentation

---

**祝你启动顺利！有问题直接问。😊**
