# 📋 腾讯云部署 - 配置清单

> 这是一份核查清单，用来跟踪部署过程中需要收集的所有信息和完成的步骤。

---

## 🔐 第 1 部分：敏感信息收集

在运行部署脚本前，请按以下清单收集所有必要的 API 密钥和凭证。

### 必填项（核心功能）

- [ ] **数据库密码** - 你要设置的强密码
  - 用途：PostgreSQL 用户密码
  - 建议：`SuperSecure@2026!` 或类似格式
  - 保存位置：`.env.production` → `DB_PASSWORD`

- [ ] **Cloudflare R2 Access Key**
  - 来源：Cloudflare 控制面板 → R2 → API 令牌
  - 用途：对象存储（图片、视频）
  - 保存位置：`.env.production` → `AWS_ACCESS_KEY_ID`

- [ ] **Cloudflare R2 Secret Key**
  - 来源：Cloudflare 控制面板 → R2 → API 令牌（同上）
  - 用途：R2 认证
  - 保存位置：`.env.production` → `AWS_SECRET_ACCESS_KEY`

- [ ] **OpenAI API Key**
  - 来源：https://platform.openai.com/account/api-keys
  - 用途：DALL-E 图片生成
  - 格式：`sk-...`
  - 保存位置：`.env.production` → `OPENAI_API_KEY`

### 可选但推荐

- [ ] **通义万相 API Key**（阿里云）
  - 来源：https://dashscope.aliyun.com
  - 用途：多模型支持
  - 保存位置：`.env.production` → `DASHSCOPE_API_KEY`

- [ ] **Stability AI API Key**
  - 来源：https://platform.stabilityai.com
  - 用途：Stability 图片生成
  - 保存位置：`.env.production` → `STABILITY_API_KEY`

### 支付相关（如需付费功能）

- [ ] **Stripe API Key（Live）**
  - 来源：https://dashboard.stripe.com/apikeys
  - 用途：信用卡支付处理
  - 保存位置：`.env.production` → `STRIPE_API_KEY`

- [ ] **Stripe Webhook Secret**
  - 来源：Stripe Dashboard → Webhooks
  - 用途：支付回调验证
  - 保存位置：`.env.production` → `STRIPE_WEBHOOK_SECRET`

- [ ] **微信支付商户 ID**
  - 来源：微信商户后台
  - 用途：微信支付
  - 保存位置：`.env.production` → `WECHAT_PAY_MERCHANT_ID`

- [ ] **微信支付 API Key**
  - 来源：微信商户后台 → API 安全
  - 用途：微信支付认证
  - 保存位置：`.env.production` → `WECHAT_PAY_API_KEY`

### 登录（OAuth）相关

- [ ] **Google OAuth Client ID**
  - 来源：https://console.cloud.google.com → Credentials
  - 格式：`xxx.apps.googleusercontent.com`
  - 保存位置：`.env.production` → `GOOGLE_OAUTH_CLIENT_ID`

- [ ] **Google OAuth Client Secret**
  - 来源：同上
  - 保存位置：`.env.production` → `GOOGLE_OAUTH_CLIENT_SECRET`

- [ ] **微信 OAuth App ID**
  - 来源：https://open.weixin.qq.com → 应用管理
  - 用途：微信登录
  - 保存位置：`.env.production` → `WECHAT_OAUTH_APPID`

- [ ] **微信 OAuth Secret**
  - 来源：同上
  - 保存位置：`.env.production` → `WECHAT_OAUTH_SECRET`

### 监控相关（可选）

- [ ] **Sentry DSN**
  - 来源：https://sentry.io → 项目设置
  - 用途：错误追踪
  - 保存位置：`.env.production` → `SENTRY_DSN`

---

## 🖥️ 第 2 部分：服务器准备

- [ ] **腾讯云轻量服务器**
  - 系统：Ubuntu 24.04 LTS 64bit ✓
  - IP：118.25.22.37 ✓
  - 用户名：ubuntu ✓
  - 密码：已收集 ✓

- [ ] **腾讯云防火墙配置**
  - [ ] 开放端口 80（HTTP）
  - [ ] 开放端口 443（HTTPS）
  - [ ] 端口 8000 可选（仅调试用）

- [ ] **域名配置**（可选）
  - [ ] 已购买域名
  - [ ] DNS A 记录指向 118.25.22.37
  - [ ] 已获得 SSL 证书（Let's Encrypt 或商业）

---

## 🚀 第 3 部分：部署执行

### 前置准备

- [ ] 已从本地运行过 `git clone --recurse-submodules https://github.com/Frankyang31/pixel.monorepo.git`
- [ ] 确认 `pixel.monorepo/service/` 目录存在
- [ ] 已收集全部敏感信息（上述第 1 部分）

### 一键部署步骤

#### 第 1 步：SSH 连接

```bash
ssh ubuntu@118.25.22.37
# 输入密码: a:SP8^+yA7v_Lg-2
```

- [ ] 成功连接到服务器

#### 第 2 步：运行部署脚本

```bash
cd /tmp
git clone --recurse-submodules https://github.com/Frankyang31/pixel.monorepo.git
cd pixel.monorepo/service
sudo bash deploy-prod.sh
```

- [ ] 脚本开始运行
- [ ] 自动安装 Docker 和 Docker Compose
- [ ] 代码克隆到 `/opt/pixel`
- [ ] 脚本在要求编辑 `.env.production` 时暂停

#### 第 3 步：配置环境变量

```bash
sudo nano /opt/pixel/service/.env.production
```

需要填入的变量（按优先级）：

**⭐ 必填（最高优先级）**
- [ ] `DB_PASSWORD` → 你设置的强密码
- [ ] `SECRET_KEY` → 随机生成的密钥
- [ ] `AWS_ACCESS_KEY_ID` → Cloudflare R2 Access Key
- [ ] `AWS_SECRET_ACCESS_KEY` → Cloudflare R2 Secret Key
- [ ] `OPENAI_API_KEY` → OpenAI API Key

**⭐⭐ 可选但推荐**
- [ ] `DASHSCOPE_API_KEY` → 通义万相密钥
- [ ] `STABILITY_API_KEY` → Stability AI 密钥
- [ ] `STRIPE_API_KEY` → Stripe 密钥（如需支付）
- [ ] `GOOGLE_OAUTH_CLIENT_ID` → Google OAuth
- [ ] `GOOGLE_OAUTH_CLIENT_SECRET` → Google OAuth

**⭐⭐⭐ 可选（低优先级）**
- [ ] `WECHAT_PAY_*` → 微信支付相关
- [ ] `WECHAT_OAUTH_*` → 微信登录相关
- [ ] `SENTRY_DSN` → 错误追踪

保存文件（Ctrl+O → Enter → Ctrl+X）：
- [ ] 文件已保存

#### 第 4 步：完成部署

```bash
sudo bash deploy-prod.sh
```

- [ ] 脚本重新运行
- [ ] 所有 6 个容器成功启动
- [ ] 数据库迁移完成
- [ ] 脚本显示"部署完成！"

#### 第 5 步：验证部署

```bash
# 查看容器状态
cd /opt/pixel/service
docker-compose -f docker-compose.prod.yml ps

# 应该看到所有容器都是 "Up"
```

- [ ] `pixel_postgres` → Up ✓
- [ ] `pixel_redis` → Up ✓
- [ ] `pixel_api` → Up ✓
- [ ] `pixel_celery_worker` → Up ✓
- [ ] `pixel_flower` → Up ✓
- [ ] `pixel_nginx` → Up ✓

#### 第 6 步：访问应用

- [ ] API 文档可访问：http://118.25.22.37:8000/docs
- [ ] 健康检查通过：http://118.25.22.37:8000/health
- [ ] Celery 监控可访问：http://118.25.22.37:5555

---

## 📱 第 4 部分：后续配置

### SSL/HTTPS 配置（如使用域名）

- [ ] 已获得 SSL 证书（Let's Encrypt）
- [ ] 已将证书复制到 `/opt/pixel/service/nginx/ssl/`
- [ ] 已编辑 `nginx/conf.d/default.conf` 启用 SSL
- [ ] 已重启 Nginx

### 域名 DNS 配置

- [ ] 域名 A 记录已指向 118.25.22.37
- [ ] DNS 解析生效（可用 `nslookup` 验证）
- [ ] 更新 `.env.production` 中的 `DOMAIN` 和 `CORS_ORIGINS`

### 监控和告警

- [ ] 在腾讯云控制面板设置 CPU 告警（> 80%）
- [ ] 设置内存告警（> 85%）
- [ ] 设置磁盘告警（> 90%）

### 定期维护计划

- [ ] 每周备份数据库
- [ ] 每月检查磁盘使用（`df -h`）
- [ ] 定期更新代码（`git pull origin main`）
- [ ] 检查日志文件大小（防止磁盘满）

---

## 🧪 第 5 部分：功能测试

### 基础功能

- [ ] API 健康检查成功
- [ ] 可访问 API 文档页面
- [ ] 可查看 Swagger UI 中的所有端点

### 数据库

- [ ] 可连接到 PostgreSQL
- [ ] 可查询数据库中的表
- [ ] 数据持久化正常（容器重启后数据仍在）

### 缓存

- [ ] Redis 连接正常
- [ ] 缓存操作成功

### 后台任务

- [ ] Celery Worker 正常运行
- [ ] 可在 Flower 监控面板看到任务
- [ ] 后台任务能正确处理

### 存储

- [ ] 可上传文件到 Cloudflare R2
- [ ] 可从 R2 下载文件

---

## ✅ 最终确认

部署完成后，请确认以下所有项目都已完成：

- [ ] 所有 6 个容器都在运行
- [ ] API 文档可访问
- [ ] 数据库迁移成功
- [ ] 敏感信息已安全保存
- [ ] 日志记录正常
- [ ] 备份计划已设置
- [ ] 监控告警已配置
- [ ] 团队成员已通知部署完成

---

## 📚 参考文档

| 文档 | 位置 | 用途 |
|------|------|------|
| 快速参考 | `TENCENT_CLOUD_QUICKSTART.md` | 常用命令和故障排查 |
| 完整指南 | `DEPLOYMENT.md` | 详细部署步骤和配置 |
| 架构总结 | `DEPLOYMENT_SUMMARY.md` | 架构图和概览 |
| 本地启动 | `README.md` / `QUICKSTART.md` | 本地开发环境 |

---

## 💬 常见问题

**Q: 忘记了某个 API 密钥怎么办？**
A: 可以稍后编辑 `.env.production` 并重启容器：
```bash
sudo nano /opt/pixel/service/.env.production
docker-compose -f docker-compose.prod.yml restart api
```

**Q: 部署失败了怎么办？**
A: 查看完整日志：
```bash
docker-compose -f docker-compose.prod.yml logs api
# 查看 DEPLOYMENT.md 的故障排查章节
```

**Q: 如何安全地存储这份清单？**
A: 建议：
- ✓ 保存到安全的位置（不要上传到 GitHub）
- ✓ 定期备份
- ✓ 使用密码管理器存储敏感信息

---

**清单版本**：v1.0
**最后更新**：2026-03-31
**部署环境**：腾讯云轻量服务器 | Ubuntu 24.04 LTS | 118.25.22.37
