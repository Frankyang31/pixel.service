# 腾讯云部署 - 快速操作指南

## 🚀 三步快速部署

### 第 1 步：连接服务器

```bash
ssh ubuntu@118.25.22.37
# 输入密码: a:SP8^+yA7v_Lg-2
```

### 第 2 步：一键部署

```bash
cd /tmp
git clone --recurse-submodules https://github.com/Frankyang31/pixel.monorepo.git
cd pixel.monorepo/service
sudo bash deploy-prod.sh
```

脚本会自动：
- ✅ 安装 Docker 和 Docker Compose
- ✅ 克隆代码到 `/opt/pixel`
- ✅ 创建必要的目录
- ✅ 提示你配置 `.env.production`

### 第 3 步：配置敏感信息

脚本首次运行会在这里停止，这是正常的。按照以下步骤：

```bash
# 编辑环境变量
nano /opt/pixel/service/.env.production

# 需要填入的关键信息：
# 1. DB_PASSWORD - 设置一个强密码（比如 SuperSecure@2026）
# 2. AWS_ACCESS_KEY_ID - 你的 Cloudflare R2 Access Key
# 3. AWS_SECRET_ACCESS_KEY - 你的 Cloudflare R2 Secret Key
# 4. OPENAI_API_KEY - 你的 OpenAI API 密钥
# 5. 其他 API 密钥和凭证...

# 保存并退出（Ctrl+O, Enter, Ctrl+X）

# 再次运行部署脚本
sudo bash deploy-prod.sh
```

---

## 📊 部署后验证

```bash
# 查看容器状态
cd /opt/pixel/service
docker-compose -f docker-compose.prod.yml ps

# 应该看到 6 个容器都在 "Up" 状态：
# pixel_postgres  - UP
# pixel_redis     - UP
# pixel_api       - UP
# pixel_celery_worker - UP
# pixel_flower    - UP
# pixel_nginx     - UP
```

## 🌐 访问应用

- **API 文档**：http://118.25.22.37:8000/docs
- **API 健康检查**：http://118.25.22.37:8000/health
- **Celery 监控面板**：http://118.25.22.37:5555
- **Nginx 日志**：/opt/pixel/service/logs/nginx/

---

## 📝 常用命令

```bash
cd /opt/pixel/service

# 查看所有日志
docker-compose -f docker-compose.prod.yml logs -f

# 查看特定服务日志
docker-compose -f docker-compose.prod.yml logs -f api

# 重启服务
docker-compose -f docker-compose.prod.yml restart api

# 进入容器调试
docker-compose -f docker-compose.prod.yml exec api bash

# 停止所有容器
docker-compose -f docker-compose.prod.yml down

# 查看容器资源使用
docker stats

# 删除所有无用的容器/镜像（清理空间）
docker system prune -a
```

---

## 🔧 更新应用代码

```bash
cd /opt/pixel

# 拉取最新代码
git pull origin main

# 重新构建应用镜像
cd service
docker-compose -f docker-compose.prod.yml build api

# 重启应用
docker-compose -f docker-compose.prod.yml up -d api

# 查看日志确保启动成功
docker-compose -f docker-compose.prod.yml logs -f api
```

---

## ⚙️ 数据库操作

```bash
cd /opt/pixel/service

# 连接到数据库
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d pixel_db

# 运行 SQL 命令（示例）
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d pixel_db -c "SELECT COUNT(*) FROM users;"

# 备份数据库
docker-compose -f docker-compose.prod.yml exec -T postgres pg_dump -U postgres pixel_db > backup.sql

# 恢复数据库
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U postgres pixel_db < backup.sql
```

---

## 🔒 SSL/HTTPS 配置（可选）

如果你有域名，按以下步骤配置 HTTPS：

```bash
# 1. 安装 Certbot
sudo apt-get install certbot python3-certbot-nginx

# 2. 申请证书（替换 your-domain.com）
sudo certbot certonly --standalone -d your-domain.com

# 3. 编辑 Nginx 配置
sudo nano /opt/pixel/service/nginx/conf.d/default.conf

# 4. 取消注释以下行并填入你的域名：
# server_name your-domain.com;
# ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
# ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

# 5. 重启 Nginx
docker-compose -f docker-compose.prod.yml restart nginx
```

---

## ❌ 故障排查

### 问题：容器无法启动
```bash
# 查看错误日志
docker-compose -f docker-compose.prod.yml logs api

# 检查 .env.production 是否有语法错误
cat .env.production | grep -E "^[A-Z_]+=.*$"
```

### 问题：无法访问 API
```bash
# 检查 Nginx 配置
docker-compose -f docker-compose.prod.yml exec nginx nginx -t

# 查看 Nginx 日志
docker-compose -f docker-compose.prod.yml logs nginx

# 检查防火墙（腾讯云控制面板）
# 确保端口 80 和 443 已开放
```

### 问题：数据库连接失败
```bash
# 检查 PostgreSQL 健康状态
docker-compose -f docker-compose.prod.yml ps | grep postgres

# 测试数据库连接
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -h localhost -d pixel_db -c "SELECT 1;"
```

### 问题：Celery 任务无法处理
```bash
# 检查 Worker 日志
docker-compose -f docker-compose.prod.yml logs celery_worker

# 查看 Flower 监控面板
# http://118.25.22.37:5555
```

---

## 📚 更多文档

- **完整部署指南**：`DEPLOYMENT.md`
- **README 启动指南**：`README.md`
- **快速启动指南**：`QUICKSTART.md`

---

## 💡 提示

1. **定期备份**：每周备份数据库
   ```bash
   docker-compose -f docker-compose.prod.yml exec -T postgres pg_dump -U postgres pixel_db | gzip > backup_$(date +%Y%m%d).sql.gz
   ```

2. **监控磁盘空间**：
   ```bash
   df -h  # 检查磁盘使用情况
   docker system df  # 检查 Docker 使用的空间
   ```

3. **定期更新代码**：
   ```bash
   cd /opt/pixel
   git pull origin main
   cd service
   docker-compose -f docker-compose.prod.yml build api
   docker-compose -f docker-compose.prod.yml up -d api
   ```

4. **设置监控告警**：
   - CPU 使用率 > 80%
   - 内存使用率 > 85%
   - 磁盘使用率 > 90%

---

**需要帮助？**联系技术支持或查阅详细的 DEPLOYMENT.md 文档。
