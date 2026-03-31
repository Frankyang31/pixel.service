# 简化版部署清单 - 仅需 3 项配置

> 针对国内用户、使用腾讯云 COS、暂时不配置 AI 模型 API 的快速部署版本

---

## 📋 必填信息清单

你需要准备以下 **3 项信息**，其他都由系统自动处理。

### ① 数据库密码（自己设置）

**用途**：保护 PostgreSQL 数据库

**如何设置**：
- 选择一个强密码（至少 12 个字符）
- 包含大小写字母、数字、特殊符号
- 例如：`SecurePass123@2026`

**填入位置**：部署时会提示

---

### ② 腾讯云 COS 配置

**用途**：存储生成的图片和视频

**需要从腾讯云获取的 2 个信息**：

| 信息 | 说明 |
|------|------|
| **SecretId** | 类似用户名（以 AKID 开头） |
| **SecretKey** | 类似密码（长串字符） |
| **Bucket 名称** | 你创建的存储桶名称（例：pixel-assets） |
| **地域代码** | 存储桶所在地（例：ap-shanghai） |

**获取步骤**：参考 `TENCENT_COS_SETUP_GUIDE.md`（5 分钟搞定）

**填入位置**：`.env.production` 文件

---

### ③ API 密钥（暂时跳过）

暂时不配置 OpenAI、通义万相等 AI 模型 API。系统有默认的本地处理能力，后续需要时再配置。

---

## ✅ 部署步骤（30 分钟）

### 第 1 步：准备信息（10 分钟）

#### 1.1 设置数据库密码
- 想一个强密码，记下来
- 例如：`SecurePass123@`

#### 1.2 创建腾讯云 COS 存储桶（5 分钟）

按照这个步骤：
1. 打开 `TENCENT_COS_SETUP_GUIDE.md`
2. 按照指南的第 1-3 步操作
3. 获取 SecretId 和 SecretKey

**检查清单**：
- [ ] 已在腾讯云控制台创建 COS 存储桶
- [ ] 已记下存储桶名称（例：pixel-assets）
- [ ] 已记下地域代码（例：ap-shanghai）
- [ ] 已获取 SecretId（以 AKID 开头）
- [ ] 已获取 SecretKey
- [ ] 已关闭或保存好这些信息（不要丢失）

---

### 第 2 步：一键部署（15 分钟）

#### 2.1 连接服务器

```bash
ssh ubuntu@118.25.22.37
```

输入密码：`a:SP8^+yA7v_Lg-2`

#### 2.2 下载代码并进入目录

```bash
cd /tmp
git clone --recurse-submodules https://github.com/Frankyang31/pixel.monorepo.git
cd pixel.monorepo/service
```

#### 2.3 运行部署脚本

```bash
sudo bash deploy-prod.sh
```

脚本会自动进行：
- ✅ 安装 Docker 和 Docker Compose
- ✅ 创建 PostgreSQL 数据库容器
- ✅ 创建 Redis 缓存容器
- ✅ 创建 Nginx 反向代理容器
- ✅ 创建 FastAPI 应用容器
- ✅ 创建 Celery Worker 容器
- ✅ 配置监控面板

#### 2.4 配置环境变量

脚本会提示你编辑 `.env.production` 文件：

```bash
sudo nano /opt/pixel/service/.env.production
```

**需要填入的内容**：

```env
# 数据库密码
DB_PASSWORD=你刚才设置的密码

# 腾讯云 COS 配置
TENCENT_COS_SECRET_ID=你的SecretId
TENCENT_COS_SECRET_KEY=你的SecretKey
TENCENT_COS_BUCKET=pixel-assets
TENCENT_COS_REGION=ap-shanghai
```

**操作说明**：
1. 用 `Ctrl+F` 找到需要修改的行
2. 删除旧值，输入新值
3. 按 `Ctrl+X` 退出
4. 按 `Y` 确认保存
5. 按 `Enter` 完成

#### 2.5 再次运行脚本完成部署

```bash
sudo bash deploy-prod.sh
```

脚本会验证所有配置，然后启动所有容器。

**完成！** ✅

---

## 🔍 验证部署成功

### 检查 1：容器状态

```bash
cd /opt/pixel/service
docker-compose -f docker-compose.prod.yml ps
```

你应该看到 6 个容器都是 **"Up"** 状态：
- postgres
- redis
- pixel-api
- pixel-worker
- flower
- nginx

### 检查 2：访问应用

在浏览器打开：

| 地址 | 用途 |
|------|------|
| `http://118.25.22.37:8000/docs` | API 文档（Swagger UI） |
| `http://118.25.22.37:8000/health` | 健康检查 |
| `http://118.25.22.37:5555` | Celery 监控面板 |

### 检查 3：查看日志

```bash
docker-compose -f docker-compose.prod.yml logs -f pixel-api
```

应该看到 "Application startup complete" 的日志。

---

## 🆘 常见问题快速解决

### Q1：脚本执行失败，提示权限不足

**解决**：确保前面加了 `sudo`
```bash
sudo bash deploy-prod.sh  # 正确
bash deploy-prod.sh       # 错误
```

### Q2：编辑 `.env.production` 时找不到字段

**解决**：用 `Ctrl+F` 搜索字段名
```bash
nano /opt/pixel/service/.env.production
# 按 Ctrl+F 搜索 "TENCENT_COS"
```

### Q3：容器启动失败，提示 "authentication failed"

**解决**：检查 COS 配置：
- SecretId 是否正确（应以 AKID 开头）
- SecretKey 是否正确
- Bucket 名称是否正确

### Q4：无法访问 API 文档

**解决**：
1. 检查容器是否都在运行：`docker-compose -f docker-compose.prod.yml ps`
2. 查看 FastAPI 日志：`docker-compose -f docker-compose.prod.yml logs pixel-api`
3. 检查防火墙是否开放了 8000 和 5555 端口

### Q5：数据库连接失败

**解决**：
1. 检查 `DB_PASSWORD` 是否正确
2. 检查 PostgreSQL 容器是否在运行
3. 查看数据库日志：`docker-compose -f docker-compose.prod.yml logs postgres`

---

## 📁 部署后的文件位置

所有数据存储在服务器的 `/opt/pixel/service/` 目录：

```
/opt/pixel/service/
├── docker-compose.prod.yml      # 容器编排文件
├── .env.production              # 你的配置文件（保管好！）
├── postgres_data/               # PostgreSQL 数据库数据
├── redis_data/                  # Redis 缓存数据
├── logs/
│   ├── nginx/                   # Nginx 访问日志
│   └── app/                     # 应用日志
└── volumes/                     # 其他容器数据
```

---

## 🚀 部署后的常用命令

### 查看容器状态
```bash
cd /opt/pixel/service
docker-compose -f docker-compose.prod.yml ps
```

### 查看实时日志
```bash
# 查看 FastAPI 日志
docker-compose -f docker-compose.prod.yml logs -f pixel-api

# 查看 Celery Worker 日志
docker-compose -f docker-compose.prod.yml logs -f pixel-worker

# 查看所有容器日志
docker-compose -f docker-compose.prod.yml logs -f
```

### 重启容器
```bash
# 重启单个容器
docker-compose -f docker-compose.prod.yml restart pixel-api

# 重启所有容器
docker-compose -f docker-compose.prod.yml restart
```

### 停止/启动所有容器
```bash
# 停止
docker-compose -f docker-compose.prod.yml down

# 启动
docker-compose -f docker-compose.prod.yml up -d
```

### 查看容器资源使用
```bash
docker stats
```

---

## 💾 数据备份

### 备份数据库

```bash
cd /opt/pixel/service

# 备份到本地
docker-compose -f docker-compose.prod.yml exec postgres pg_dump \
  -U postgres pixel_db > backup_$(date +%Y%m%d).sql
```

### 恢复数据库

```bash
# 从备份恢复
docker-compose -f docker-compose.prod.yml exec -T postgres psql \
  -U postgres pixel_db < backup_20260331.sql
```

---

## 📞 需要帮助？

遇到问题时的排查步骤：

1. **查看日志** → 通常能发现问题原因
2. **检查配置** → 确保 `.env.production` 中的 COS 配置正确
3. **检查防火墙** → 确保腾讯云防火墙允许 80、443、8000 端口
4. **重启容器** → 有时候重启能解决临时问题

---

## ✨ 现在你已准备好了！

所有部署文件都已准备完毕。**可以立即开始部署！**

**下一步流程**：
1. 打开 `TENCENT_COS_SETUP_GUIDE.md` 创建 COS 存储桶（5 分钟）
2. 回到本文档，按照第 1-2 步操作（30 分钟）
3. 访问 http://118.25.22.37:8000/docs 验证成功 ✅

**祝部署顺利！** 🚀
