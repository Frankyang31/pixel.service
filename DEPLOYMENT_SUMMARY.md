# 🚀 腾讯云部署方案 - 完整总结

## 📊 部署架构图

```
┌─────────────────────────────────────────────────────┐
│          腾讯云轻量服务器（Ubuntu 24.04）            │
│         IP: 118.25.22.37 | 用户: ubuntu              │
├─────────────────────────────────────────────────────┤
│                                                       │
│  ┌────────────────────────────────────────────────┐  │
│  │        Nginx 反向代理 (容器)                   │  │
│  │  - 监听 0.0.0.0:80/443                        │  │
│  │  - 转发 → FastAPI (127.0.0.1:8000)            │  │
│  │  - SSE 支持 (长连接)                          │  │
│  │  - Flower 路由 (/flower/)                    │  │
│  │  - 安全头 + 日志滚动                          │  │
│  └────────────────────────────────────────────────┘  │
│                         ↓                            │
│  ┌─────────────────────────────────────────────────┐ │
│  │  FastAPI 应用 (127.0.0.1:8000)                 │ │
│  │  - 4 个 Uvicorn workers                        │ │
│  │  - 健康检查 /health ✓                          │ │
│  │  - 自动文档 /docs                              │ │
│  │  - 异步处理                                    │ │
│  └──────────────┬──────────────────────────────────┘ │
│                 ↓                                    │
│  ┌──────────────────────────────────────────────┐   │
│  │  PostgreSQL 数据库                           │   │
│  │  - 127.0.0.1:5432 (本地只)                  │   │
│  │  - 200 连接 + 性能优化                       │   │
│  │  - 数据持久化                                │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │  Redis 缓存 + 队列                           │   │
│  │  - 127.0.0.1:6379 (本地只)                  │   │
│  │  - 512MB 内存限制 (LRU 清理)                │   │
│  │  - 数据持久化 (AOF)                         │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │  Celery Worker (后台任务处理)                │   │
│  │  - 4 并发处理                                │   │
│  │  - 图片/视频生成队列                        │   │
│  │  - 自动重启                                 │   │
│  │  - 日志滚动策略 (50MB x 5)                 │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │  Celery Flower (监控面板)                   │   │
│  │  - 127.0.0.1:5555 → Nginx /flower/         │   │
│  │  - 实时任务监控                             │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

## 🎯 部署文件清单

| 文件 | 位置 | 用途 |
|------|------|------|
| **deploy-prod.sh** | `service/` | 一键部署脚本（自动化全流程） |
| **docker-compose.prod.yml** | `service/` | 生产容器编排配置 |
| **nginx/conf.d/default.conf** | `service/` | Nginx 反向代理配置 |
| **.env.production.example** | `service/` | 生产环境变量模板 |
| **DEPLOYMENT.md** | `service/` | 完整部署指南（270+ 行） |
| **TENCENT_CLOUD_QUICKSTART.md** | `service/` | 快速参考（常用命令和故障排查） |

---

## ⚡ 快速开始

### 第 1 步：连接服务器
```bash
ssh ubuntu@118.25.22.37
# 密码: a:SP8^+yA7v_Lg-2
```

### 第 2 步：运行部署脚本
```bash
cd /tmp
git clone --recurse-submodules https://github.com/Frankyang31/pixel.monorepo.git
cd pixel.monorepo/service
sudo bash deploy-prod.sh
```

### 第 3 步：配置敏感信息
```bash
# 脚本会在这里暂停，要求编辑 .env.production
# 使用以下命令编辑：
sudo nano /opt/pixel/service/.env.production

# 需要填入（获取方式）：
# - DB_PASSWORD → 自己设置强密码
# - AWS_ACCESS_KEY_ID → Cloudflare R2
# - AWS_SECRET_ACCESS_KEY → Cloudflare R2
# - OPENAI_API_KEY → OpenAI 控制面板
# - STRIPE_API_KEY → Stripe Dashboard
# - GOOGLE_OAUTH_CLIENT_ID → Google Cloud Console
# - WECHAT_OAUTH_APPID → 微信开放平台
# - 其他 API 密钥...

# 保存并退出（Ctrl+O → Enter → Ctrl+X）
```

### 第 4 步：完成部署
```bash
sudo bash deploy-prod.sh
```

---

## ✅ 部署验证

```bash
# 查看容器状态
cd /opt/pixel/service
docker-compose -f docker-compose.prod.yml ps

# 应该看到 6 个容器都是 "Up"
# ✓ pixel_postgres
# ✓ pixel_redis
# ✓ pixel_api
# ✓ pixel_celery_worker
# ✓ pixel_flower
# ✓ pixel_nginx
```

## 🌐 访问应用

| 服务 | 地址 | 用途 |
|------|------|------|
| **API 文档** | http://118.25.22.37:8000/docs | 测试 API 端点 |
| **API 健康检查** | http://118.25.22.37:8000/health | 验证服务状态 |
| **Celery 监控** | http://118.25.22.37:5555 | 查看后台任务 |
| **Nginx 日志** | `/opt/pixel/service/logs/nginx/` | 访问日志 |

---

## 📁 部署后的目录结构

```
/opt/pixel/
├── service/                      # 后端项目
│   ├── app/                      # 应用代码
│   ├── .env.production           # 敏感配置（已编辑）
│   ├── docker-compose.prod.yml   # 容器编排
│   ├── Dockerfile                # 应用镜像
│   ├── nginx/
│   │   ├── conf.d/default.conf  # Nginx 配置
│   │   └── ssl/                 # SSL 证书（如已配置）
│   ├── logs/                     # 应用日志
│   │   ├── nginx/               # Nginx 日志
│   │   └── (FastAPI/Celery 日志)
│   ├── postgres_data/            # 数据库数据（持久化）
│   ├── redis_data/               # Redis 数据（持久化）
│   └── ...
├── web/                          # 前端项目（submodule）
├── .gitmodules                   # Submodule 配置
└── ...
```

---

## 🔧 常用命令速查

```bash
cd /opt/pixel/service

# ━━━ 容器管理 ━━━
docker-compose -f docker-compose.prod.yml ps              # 查看容器
docker-compose -f docker-compose.prod.yml logs -f api     # 查看 API 日志
docker-compose -f docker-compose.prod.yml restart api     # 重启 API
docker-compose -f docker-compose.prod.yml down            # 停止全部

# ━━━ 代码更新 ━━━
cd /opt/pixel
git pull origin main                                       # 拉取代码
cd service
docker-compose -f docker-compose.prod.yml build api       # 重建镜像
docker-compose -f docker-compose.prod.yml up -d api       # 启动

# ━━━ 数据库 ━━━
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d pixel_db
# 然后可以运行 SQL 命令

# 备份
docker-compose -f docker-compose.prod.yml exec -T postgres pg_dump -U postgres pixel_db > backup.sql

# ━━━ 监控 ━━━
docker stats                                              # 实时资源使用
docker-compose -f docker-compose.prod.yml logs api       # API 日志
curl http://localhost:8000/health                         # 健康检查
```

---

## 🔒 关键安全要点

### ✅ 已配置的安全措施

- ✓ 数据库仅本地连接（127.0.0.1:5432）
- ✓ Redis 仅本地连接（127.0.0.1:6379）
- ✓ FastAPI 仅本地连接（127.0.0.1:8000）
- ✓ 非 root 用户运行应用（appuser）
- ✓ Nginx 安全头（X-Frame-Options、CSP 等）
- ✓ 数据库连接池限制（200 连接）

### 🔐 待完成的安全配置

- [ ] 配置 SSL/HTTPS 证书（Let's Encrypt 或自签）
- [ ] 在腾讯云防火墙中只开放 80/443 端口
- [ ] 定期备份数据库
- [ ] 配置 Sentry 错误追踪（可选）
- [ ] 启用 Prometheus 监控（可选）

---

## 🚨 故障排查速查

| 问题 | 症状 | 解决 |
|------|------|------|
| **容器无法启动** | `Exit 1` | `docker-compose logs api` 查看错误 |
| **无法访问 API** | 连接超时 | 检查 Nginx 配置：`docker-compose exec nginx nginx -t` |
| **数据库连接失败** | `connection refused` | 检查 PostgreSQL：`docker-compose logs postgres` |
| **Celery 任务卡住** | Flower 显示 `PENDING` | 查看 Worker 日志：`docker-compose logs celery_worker` |
| **磁盘空间满** | 容器无法写入 | 清理日志或删除旧镜像 |

详见 `DEPLOYMENT.md` 的"故障排查"章节。

---

## 📚 完整文档位置

| 文档 | 适用场景 |
|------|---------|
| **TENCENT_CLOUD_QUICKSTART.md** | 快速上手（常用命令） |
| **DEPLOYMENT.md** | 完整部署流程（详细步骤） |
| **README.md** | 本地开发启动 |
| **QUICKSTART.md** | 三步快速本地启动 |

---

## 💡 后续建议

1. **定期备份**（每周）
   ```bash
   docker-compose -f docker-compose.prod.yml exec -T postgres pg_dump -U postgres pixel_db | gzip > backup_$(date +%Y%m%d).sql.gz
   ```

2. **监控资源**（每月）
   ```bash
   df -h          # 磁盘使用
   docker system df  # Docker 使用
   ```

3. **更新代码**（按需）
   ```bash
   cd /opt/pixel && git pull origin main
   cd service && docker-compose -f docker-compose.prod.yml build api
   docker-compose -f docker-compose.prod.yml up -d api
   ```

4. **监控告警**（腾讯云控制面板）
   - CPU > 80% 告警
   - 内存 > 85% 告警
   - 磁盘 > 90% 告警

---

## 📞 需要帮助？

- 查看详细部署指南：`cat /opt/pixel/service/DEPLOYMENT.md`
- 查看容器日志：`docker-compose -f docker-compose.prod.yml logs -f`
- 进入容器调试：`docker-compose -f docker-compose.prod.yml exec api bash`
- 访问 API 文档：http://118.25.22.37:8000/docs

---

**部署时间**：约 10-15 分钟（首次）
**维护工作量**：最小（Docker 自动管理）
**扩展性**：支持添加更多 Worker 实例或数据库副本

🎉 你的后端已准备好在腾讯云上运行了！
