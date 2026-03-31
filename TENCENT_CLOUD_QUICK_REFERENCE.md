# 腾讯云部署 - 快速参考卡

> 适用于国内用户，使用腾讯云 COS 对象存储，简化配置到只需 3 项必填

## 📋 3 项必填配置

| # | 项目 | 来源 | 例子 |
|---|------|------|------|
| 1 | 数据库密码 | 自己设置 | `SecurePass123@` |
| 2 | 腾讯云 COS SecretId | 腾讯云控制台 | `AKIDxxxxxxxxxxxx` |
| 3 | 腾讯云 COS SecretKey | 腾讯云控制台 | `xxxxxxxxxxxx` |

## 🚀 3 步快速部署（30 分钟）

### 第 1 步：创建腾讯云 COS（5 分钟）

参考：`TENCENT_COS_SETUP_GUIDE.md`

获取到：
- ✅ 存储桶名称
- ✅ SecretId
- ✅ SecretKey
- ✅ 地域代码

### 第 2 步：SSH 连接服务器（2 分钟）

```bash
ssh ubuntu@118.25.22.37
# 输入密码: a:SP8^+yA7v_Lg-2
```

### 第 3 步：运行部署脚本（20 分钟）

```bash
cd /tmp
git clone --recurse-submodules https://github.com/Frankyang31/pixel.monorepo.git
cd pixel.monorepo/service
sudo bash deploy-prod.sh
```

脚本会自动：
- 安装 Docker/Docker Compose
- 启动 6 个容器
- 提示你编辑 `.env.production`
- 运行数据库迁移
- 验证服务状态

## ✅ 验证部署成功

### 方法 1：检查容器

```bash
docker-compose -f docker-compose.prod.yml ps
# 应看到 6 个容器都是 Up
```

### 方法 2：访问 API

http://118.25.22.37:8000/docs

应该看到 Swagger UI 的 API 文档

### 方法 3：查看日志

```bash
docker-compose -f docker-compose.prod.yml logs -f pixel-api
```

应看到 "Application startup complete"

## 📚 详细文档

| 文档 | 用途 | 耗时 |
|------|------|------|
| **TENCENT_COS_SETUP_GUIDE.md** | 如何创建 COS 存储桶 | 5 分钟 |
| **SIMPLIFIED_DEPLOYMENT_CHECKLIST.md** | 完整的部署清单和故障排查 | 20 分钟 |
| **FIRST_DEPLOYMENT_GUIDE.md** | 新手详细指南（保留以备查阅） | 30 分钟 |

## 🆘 常见问题

### "authentication failed" 错误

检查 COS 配置：
- SecretId/Key 是否正确
- Bucket 名称是否正确
- 地域代码是否正确

### 无法访问 API 文档

1. 检查容器是否都在运行
2. 查看防火墙设置
3. 查看日志找原因

### 编辑 `.env.production` 时迷茫

按照这个顺序找到并填写：
```
DB_PASSWORD=你的密码
TENCENT_COS_SECRET_ID=你的SecretId
TENCENT_COS_SECRET_KEY=你的SecretKey
TENCENT_COS_BUCKET=pixel-assets
TENCENT_COS_REGION=ap-shanghai
```

## 📦 部署架构

```
Nginx (80/443)
  ↓
FastAPI (8000)
  ├─ PostgreSQL (本地数据库)
  ├─ Redis (本地缓存)
  ├─ Celery Worker (后台任务)
  └─ Celery Flower (监控面板)
```

所有数据存储：`/opt/pixel/service/`

## 🎯 部署后的访问地址

| 服务 | 地址 | 用途 |
|------|------|------|
| API 文档 | http://118.25.22.37:8000/docs | 查看和测试 API |
| 健康检查 | http://118.25.22.37:8000/health | 检查服务状态 |
| 监控面板 | http://118.25.22.37:5555 | 查看 Celery 任务 |

## 💾 日常维护命令

```bash
# 查看实时日志
docker-compose -f docker-compose.prod.yml logs -f pixel-api

# 重启应用
docker-compose -f docker-compose.prod.yml restart pixel-api

# 查看容器资源使用
docker stats

# 备份数据库
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U postgres pixel_db > backup.sql
```

## ⏱️ 时间规划

```
准备阶段（15 分钟）
  └─ 创建腾讯云 COS            (5 分钟)
  └─ 设置数据库密码             (1 分钟)
  └─ 准备 3 项配置信息          (2 分钟)

部署阶段（20 分钟）
  └─ SSH 连接服务器             (2 分钟)
  └─ 下载代码                   (3 分钟)
  └─ 运行部署脚本               (10 分钟)
  └─ 编辑配置文件               (3 分钟)
  └─ 等待容器启动               (2 分钟)

验证阶段（5 分钟）
  └─ 检查容器状态               (1 分钟)
  └─ 访问 API 文档              (2 分钟)
  └─ 查看日志确认正常           (2 分钟)

总耗时：40 分钟
```

---

**现在可以开始部署了！** 🚀

首先打开 `TENCENT_COS_SETUP_GUIDE.md` 创建存储桶。
