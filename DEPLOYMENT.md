# Pixel AI 内容生成平台 - 腾讯云生产部署指南

## 📋 目录
1. [部署前检查清单](#部署前检查清单)
2. [快速部署（3 步）](#快速部署3-步)
3. [详细部署步骤](#详细部署步骤)
4. [配置说明](#配置说明)
5. [监控和维护](#监控和维护)
6. [故障排查](#故障排查)
7. [SSL 证书配置](#ssl-证书配置)

---

## 部署前检查清单

在部署前，请确保你已经准备了以下内容：

### 🔐 敏感信息收集

| 项目 | 来源 | 用途 |
|------|------|------|
| Cloudflare R2 Access Key | Cloudflare 控制面板 | 对象存储（图片、视频） |
| Cloudflare R2 Secret Key | Cloudflare 控制面板 | 对象存储认证 |
| OpenAI API Key | platform.openai.com | DALL-E 图片生成 |
| 通义万相 API Key | dashscope.aliyun.com | 阿里通义图片生成 |
| Stability AI Key | platform.stabilityai.com | Stability AI 图片生成 |
| Stripe API Key | dashboard.stripe.com | 支付处理 |
| 微信支付商户 ID | 微信商户后台 | 微信支付 |
| Google OAuth 凭证 | console.cloud.google.com | 谷歌登录 |
| 微信 OAuth 凭证 | 微信开放平台 | 微信登录 |
| Sentry DSN | sentry.io | 错误追踪 |

### 🖥️ 服务器准备

- [ ] 腾讯云轻量服务器 1 台（Ubuntu 24.04 LTS，至少 2GB RAM，推荐 4GB+）
- [ ] 弹性 IP（可选，用于固定外网 IP）
- [ ] 域名（可选，用于 HTTPS）
- [ ] SSL 证书（如果使用域名）

---

## 快速部署（3 步）

### 第 1 步：SSH 连接到服务器

```bash
ssh ubuntu@118.25.22.37
# 输入密码: a:SP8^+yA7v_Lg-2
```

### 第 2 步：下载并运行部署脚本

```bash
cd /tmp
git clone --recurse-submodules https://github.com/Frankyang31/pixel.monorepo.git
cd pixel.monorepo/service

# 查看部署脚本
cat deploy-prod.sh

# 运行部署脚本（需要 sudo）
sudo bash deploy-prod.sh
```

### 第 3 步：配置环境变量

部署脚本首次运行会失败（因为 `.env.production` 不存在），这是正常的。

```bash
# 复制示例文件
cp .env.production.example .env.production

# 编辑环境变量（用你的真实值替换占位符）
sudo nano .env.production

# 再次运行部署脚本
sudo bash deploy-prod.sh
```

---

## 详细部署步骤

### 第 1 步：基础环境检查和安装

部署脚本会自动检查和安装：
- Docker
- Docker Compose
- Git

### 第 2 步：克隆代码仓库

脚本会将代码克隆到 `/opt/pixel` 目录：

```
/opt/pixel/
├── service/          # 后端项目
│   ├── app/
│   ├── docker-compose.prod.yml
│   ├── Dockerfile
│   ├── .env.production
│   └── ...
├── web/              # 前端项目（submodule）
├── .gitmodules
└── ...
```

### 第 3 步：配置环境变量

关键环节！需要填入所有敏感信息：

```bash
sudo nano /opt/pixel/service/.env.production
```

必填项：
- `DB_PASSWORD` - 数据库强密码
- `SECRET_KEY` - 应用密钥
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` - R2 存储
- `OPENAI_API_KEY` - OpenAI 密钥
- `STRIPE_API_KEY` - Stripe 密钥
- 其他 OAuth 和支付凭证

### 第 4 步：启动容器

```bash
cd /opt/pixel/service

# 使用生产级配置启动
docker-compose -f docker-compose.prod.yml up -d

# 查看容器状态
docker-compose -f docker-compose.prod.yml ps
```

输出应该显示 6 个容器都在运行：
- `pixel_postgres` - 数据库
- `pixel_redis` - 缓存
- `pixel_api` - FastAPI 应用
- `pixel_celery_worker` - Celery Worker
- `pixel_flower` - Celery 监控
- `pixel_nginx` - 反向代理

### 第 5 步：运行数据库迁移

```bash
cd /opt/pixel/service

# 运行 Alembic 迁移
docker-compose -f docker-compose.prod.yml exec -T api alembic upgrade head

# 查看迁移日志
docker-compose -f docker-compose.prod.yml logs api
```

### 第 6 步：验证部署

```bash
# 检查 FastAPI 健康状态
curl http://118.25.22.37:8000/health

# 查看 API 文档
# 在浏览器打开: http://118.25.22.37:8000/docs

# 查看 Celery 监控面板
# 在浏览器打开: http://118.25.22.37:5555
```

---

## 配置说明

### Nginx 配置

Nginx 配置位于：`/opt/pixel/service/nginx/conf.d/default.conf`

主要特性：
- **反向代理** - 将请求转发到 FastAPI 应用
- **SSE 支持** - 实时任务状态推送
- **Flower 监控** - Celery 任务监控面板
- **安全头** - CORS、X-Frame-Options 等
- **日志** - 保存到 `/opt/pixel/service/logs/nginx/`

### 数据持久化

重要数据存储位置：

```
/opt/pixel/service/
├── logs/                      # 应用日志
│   ├── nginx/
│   └── (FastAPI/Celery 日志)
├── postgres_data/             # PostgreSQL 数据
├── redis_data/                # Redis 数据
```

**备份建议**：定期备份这些目录。

---

## 监控和维护

### 查看日志

```bash
cd /opt/pixel/service

# 查看所有日志
docker-compose -f docker-compose.prod.yml logs -f

# 只查看 FastAPI 日志
docker-compose -f docker-compose.prod.yml logs -f api

# 只查看 Celery 日志
docker-compose -f docker-compose.prod.yml logs -f celery_worker

# 只查看 Nginx 日志
docker-compose -f docker-compose.prod.yml logs -f nginx
```

### 容器管理

```bash
cd /opt/pixel/service

# 查看容器状态
docker-compose -f docker-compose.prod.yml ps

# 重启某个容器（比如重启 API）
docker-compose -f docker-compose.prod.yml restart api

# 进入容器 shell（调试用）
docker-compose -f docker-compose.prod.yml exec api bash

# 查看容器资源使用
docker stats
```

### 更新应用代码

```bash
cd /opt/pixel

# 拉取最新代码
git pull origin main

# 重新构建镜像
cd service
docker-compose -f docker-compose.prod.yml build api

# 重启应用
docker-compose -f docker-compose.prod.yml up -d api
```

### 定期任务

建议使用 `crontab` 设置定期备份：

```bash
# 编辑 cron 任务
crontab -e

# 添加以下行（每天凌晨 2 点备份）
0 2 * * * /opt/pixel/service/backup.sh
```

---

## 故障排查

### 1. 容器无法启动

**症状**：`docker-compose ps` 显示容器状态为 `Exit 1`

**解决**：
```bash
# 查看详细错误日志
docker-compose -f docker-compose.prod.yml logs api

# 检查 .env.production 是否正确
cat /opt/pixel/service/.env.production
```

### 2. 数据库连接失败

**症状**：`ERROR: could not connect to database`

**解决**：
```bash
# 检查 PostgreSQL 容器是否健康
docker-compose -f docker-compose.prod.yml ps | grep postgres

# 查看数据库日志
docker-compose -f docker-compose.prod.yml logs postgres

# 验证数据库连接
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -h localhost -d pixel_db -c "SELECT 1;"
```

### 3. Redis 连接失败

**症状**：`Cannot connect to Redis`

**解决**：
```bash
# 检查 Redis 容器
docker-compose -f docker-compose.prod.yml ps | grep redis

# 测试 Redis 连接
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping
```

### 4. API 无法访问

**症状**：访问 `http://118.25.22.37:8000` 超时

**解决**：
```bash
# 检查 Nginx 和 API 容器
docker-compose -f docker-compose.prod.yml ps | grep -E "api|nginx"

# 检查 Nginx 配置
docker-compose -f docker-compose.prod.yml exec nginx nginx -t

# 检查 Nginx 日志
docker-compose -f docker-compose.prod.yml logs nginx
```

### 5. Celery 任务无法处理

**症状**：Flower 中任务显示 `PENDING`

**解决**：
```bash
# 检查 Worker 是否正常运行
docker-compose -f docker-compose.prod.yml logs celery_worker

# 检查 Redis 中是否有消息堆积
docker-compose -f docker-compose.prod.yml exec redis redis-cli LLEN celery

# 重启 Worker
docker-compose -f docker-compose.prod.yml restart celery_worker
```

---

## SSL 证书配置

### 方案 A：Let's Encrypt（推荐）

```bash
# 安装 Certbot
sudo apt-get install certbot python3-certbot-nginx

# 申请证书（需要域名和访问权限）
sudo certbot certonly --standalone -d your-domain.com

# 证书路径
# 公钥: /etc/letsencrypt/live/your-domain.com/fullchain.pem
# 私钥: /etc/letsencrypt/live/your-domain.com/privkey.pem

# 更新 Nginx 配置
sudo nano /opt/pixel/service/nginx/conf.d/default.conf

# 取消注释 SSL 配置并填入证书路径
# ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
# ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

# 重启 Nginx
docker-compose -f docker-compose.prod.yml restart nginx

# 自动续期（Let's Encrypt 证书需要每 90 天续期一次）
sudo crontab -e
# 添加: 0 0 1 * * certbot renew --quiet
```

### 方案 B：自签证书（开发/测试）

```bash
# 生成自签证书
openssl req -x509 -newkey rsa:4096 -nodes -out /opt/pixel/service/nginx/ssl/cert.pem -keyout /opt/pixel/service/nginx/ssl/key.pem -days 365

# 更新 Nginx 配置后重启
docker-compose -f docker-compose.prod.yml restart nginx
```

---

## 后续配置

### 1. 配置域名 DNS

如果你有域名，将 A 记录指向你的服务器 IP `118.25.22.37`。

### 2. 配置腾讯云防火墙

在腾讯云控制面板开放端口：
- 80 (HTTP)
- 443 (HTTPS)
- 8000 (API 调试，可选)
- 5555 (Flower 监控，可选)

### 3. 配置监控告警

在腾讯云设置服务器监控，关注：
- CPU 使用率
- 内存使用率
- 磁盘使用率
- 网络流量

### 4. 定期备份

```bash
# 创建备份脚本
cat > /opt/pixel/service/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backups/pixel"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# 备份数据库
docker-compose -f docker-compose.prod.yml exec -T postgres pg_dump -U postgres pixel_db | gzip > $BACKUP_DIR/db_$TIMESTAMP.sql.gz

# 备份 Redis
docker-compose -f docker-compose.prod.yml exec -T redis redis-cli BGSAVE
docker cp pixel_redis:/data/dump.rdb $BACKUP_DIR/redis_$TIMESTAMP.rdb

echo "Backup completed: $BACKUP_DIR"
EOF

chmod +x /opt/pixel/service/backup.sh
```

---

## 常见问题

### Q: 如何修改数据库密码？
A: 修改 `.env.production` 中的 `DB_PASSWORD`，然后重新启动容器。**注意**：这会导致现有连接断开，旧数据不可访问。

### Q: 如何扩展存储空间？
A: 在腾讯云控制面板扩展云硬盘，然后重启服务器。

### Q: 如何增加并发处理能力？
A: 增加 Celery Worker 实例或 FastAPI 工作进程数，修改 `docker-compose.prod.yml` 中的 `--concurrency` 参数。

### Q: 如何处理突发流量？
A: 配置腾讯云的自动扩展和负载均衡（如果使用多个实例）。

---

## 获取帮助

- 查看日志：`docker-compose logs -f`
- 检查容器：`docker-compose ps`
- 进入容器：`docker-compose exec api bash`
- FastAPI 文档：`http://118.25.22.37:8000/docs`
- Celery 监控：`http://118.25.22.37:5555`

如有问题，请查阅 README.md 或联系技术支持。
