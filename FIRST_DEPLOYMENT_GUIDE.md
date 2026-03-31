# 🎯 从 0 到 1：首次部署完整攻略

> 这是一份**从零开始**的部署指南，面向没有部署经验的用户。包含每一步的详细说明和截图位置。

---

## 📌 总体流程图

```
第 1 阶段：准备工作（需要 15 分钟）
  ├─ 收集 API 密钥和凭证
  ├─ 验证服务器连接
  └─ 下载部署脚本

          ↓

第 2 阶段：一键部署（需要 10 分钟）
  ├─ SSH 连接到服务器
  ├─ 运行自动化部署脚本
  └─ 脚本自动处理所有配置

          ↓

第 3 阶段：手动配置（需要 5 分钟）
  ├─ 编辑 .env.production
  ├─ 填入 API 密钥
  └─ 保存文件

          ↓

第 4 阶段：完成部署（需要 5 分钟）
  ├─ 再次运行脚本
  ├─ 等待容器启动
  └─ 验证服务

          ↓

完成 ✅（总耗时：35 分钟）
```

---

## 第 1 阶段：准备工作（15 分钟）

### 步骤 1.1：验证你的服务器信息

打开腾讯云控制面板，找到你的轻量服务器：

**需要记下以下信息：**

```
IP 地址：118.25.22.37 ← 记下这个
系统：Ubuntu 24.04 LTS 64bit
用户名：ubuntu ← 记下这个
登录方式：密码 ← 记下这个
```

### 步骤 1.2：收集必填的 API 密钥

你需要 5 个关键的 API 密钥。按照以下步骤一个一个获取：

#### 必填 #1：Cloudflare R2（对象存储）

1. 打开 https://dash.cloudflare.com
2. 选择你的账户和域名
3. 左侧导航栏 → R2（对象存储）
4. 右上角 → "创建 API 令牌"
5. 选择 "Edit R2" 权限
6. 复制以下信息：
   - **Access Key ID**：`e1a2b3c4...`
   - **Secret Access Key**：`1a2b3c4d...`
   
   ✅ 保存到记事本

#### 必填 #2：OpenAI API Key（图片生成）

1. 打开 https://platform.openai.com/account/api-keys
2. 点击 "Create new secret key"
3. 复制显示的密钥：`sk-proj-abc123...`

   ✅ 保存到记事本

#### 必填 #3：数据库密码

这个**不用**去任何地方获取，你自己设置：

```
建议密码格式：SuperSecure@2026!
最少 12 个字符
包含大小写字母和特殊符号
```

   ✅ 写在记事本上

#### 可选但推荐 #4-5：其他 API 密钥

如果你计划使用以下功能，现在也可以获取：

- **通义万相**（阿里云多模型）：https://dashscope.aliyun.com
- **Stability AI**（备用图片生成）：https://platform.stabilityai.com
- **Google OAuth**（谷歌登录）：https://console.cloud.google.com

   ✅ 按需收集

---

## 第 2 阶段：一键部署（10 分钟）

### 步骤 2.1：打开终端并 SSH 连接

**macOS/Linux 用户：**

打开终端，运行：
```bash
ssh ubuntu@118.25.22.37
```

然后输入密码：
```
a:SP8^+yA7v_Lg-2
```

**如果看到类似的提示，输入 `yes`：**
```
The authenticity of host '118.25.22.37' can't be established.
Are you sure you want to continue connecting (yes/no)?
```

✅ 成功连接后，你会看到类似的提示符：
```
ubuntu@VM-4-2-ubuntu:~$
```

### 步骤 2.2：下载并运行部署脚本

复制以下命令并粘贴到终端，然后按 Enter：

```bash
cd /tmp && git clone --recurse-submodules https://github.com/Frankyang31/pixel.monorepo.git && cd pixel.monorepo/service && sudo bash deploy-prod.sh
```

**脚本会自动：**
- ✓ 检查 Docker 和 Docker Compose
- ✓ 安装缺失的工具
- ✓ 克隆代码到 `/opt/pixel`
- ✓ 创建必要的目录

### 步骤 2.3：等待脚本暂停

脚本会在这里停止：

```
⚠️  .env.production 不存在，复制示例文件...
⚠️  请编辑 .env.production 并填入正确的敏感信息（数据库密码、API 密钥等）
编辑命令: nano /opt/pixel/service/.env.production
```

这是**正常的**，说明脚本已经做好准备。现在到第 3 阶段。

---

## 第 3 阶段：手动配置（5 分钟）

### 步骤 3.1：编辑环境变量文件

在终端运行（已经在第 2.2 步中看到过）：

```bash
sudo nano /opt/pixel/service/.env.production
```

你会看到一个文本编辑器，里面有很多配置项。

### 步骤 3.2：填入必填的 API 密钥

找到以下行，并用你在第 1 阶段收集的信息替换：

```bash
# 🔴 需要改：数据库密码（你自己设置的）
DB_PASSWORD=SuperSecure@2026!

# 🔴 需要改：Cloudflare R2 Access Key
AWS_ACCESS_KEY_ID=e1a2b3c4d5f6g7h8i9j0

# 🔴 需要改：Cloudflare R2 Secret Key
AWS_SECRET_ACCESS_KEY=1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p

# 🔴 需要改：OpenAI API Key
OPENAI_API_KEY=sk-proj-abc123def456

# 其他可选项保持默认或按需填入
```

### 步骤 3.3：保存文件

按 `Ctrl + X` 键，然后按 `Y`，再按 `Enter`：

```
^X: 按住 Ctrl 和 X
Y: 按 Y 确认保存
Enter: 确认文件名
```

✅ 看到 `ubuntu@VM-...$ ` 提示符说明已保存。

---

## 第 4 阶段：完成部署（5 分钟）

### 步骤 4.1：再次运行部署脚本

输入以下命令：

```bash
cd /opt/pixel/service && sudo bash deploy-prod.sh
```

### 步骤 4.2：等待脚本运行

脚本会依次：
1. 检查环境 ✓
2. 拉取代码 ✓
3. 验证 .env.production ✓
4. 创建目录 ✓
5. 启动容器（需要 1-2 分钟）
6. 运行数据库迁移 ✓
7. 验证健康状态 ✓

你会看到很多日志输出，这是**正常的**。

### 步骤 4.3：验证部署成功

当脚本运行完后，会显示：

```
✅ 部署完成！

后续步骤:

1. 访问 API: http://118.25.22.37:8000/docs

2. 查看日志:
   docker-compose -f docker-compose.prod.yml logs -f api

3. 进入容器 shell:
   docker-compose -f docker-compose.prod.yml exec api bash

4. 停止服务:
   docker-compose -f docker-compose.prod.yml down

5. 查看更多命令:
   cat /opt/pixel/service/DEPLOYMENT.md
```

### 步骤 4.4：验证所有容器都在运行

在终端运行：

```bash
docker-compose -f docker-compose.prod.yml ps
```

你应该看到类似的输出：

```
NAME                COMMAND                  STATUS
pixel_postgres      postgres                 Up 2 minutes
pixel_redis         redis-server             Up 2 minutes
pixel_api           uvicorn app.main:app     Up 1 minute
pixel_celery_worker celery -A app.core...    Up 1 minute
pixel_flower        celery -A app.core...    Up 1 minute
pixel_nginx         nginx -g daemon off      Up 1 minute
```

✅ 所有都显示 `Up` 表示成功！

---

## 第 5 阶段：验证和访问（可选）

### 访问 API 文档

在浏览器打开：

```
http://118.25.22.37:8000/docs
```

你应该看到 FastAPI 的 Swagger UI 界面，显示所有 API 端点。

### 检查服务健康

在浏览器打开：

```
http://118.25.22.37:8000/health
```

应该看到简单的响应：
```
OK
```

### 访问 Celery 监控面板（可选）

在浏览器打开：

```
http://118.25.22.37:5555
```

这是任务队列的监控面板。

---

## ❌ 如果出错了怎么办？

### 错误 #1：无法 SSH 连接

**症状：**
```
ssh: connect to host 118.25.22.37 port 22: Connection refused
```

**原因和解决：**
- ❌ 服务器网络不通
- ❌ 防火墙阻止了 22 端口
- ✓ 检查腾讯云控制面板，确保服务器已启动
- ✓ 稍等 30 秒后重试

### 错误 #2：密码错误

**症状：**
```
Permission denied, please try again.
```

**原因和解决：**
- ❌ 输入了错误的密码
- ✓ 密码是：`a:SP8^+yA7v_Lg-2`（包含特殊符号，注意复制）
- ✓ 重试

### 错误 #3：容器无法启动

**症状：**
脚本完成后，某个容器显示 `Exit 1`

**原因和解决：**
- ❌ `.env.production` 配置有误
- ✓ 查看日志：`docker-compose -f docker-compose.prod.yml logs api`
- ✓ 检查 `.env.production` 中是否有特殊字符需要转义

### 错误 #4：无法访问 API

**症状：**
访问 http://118.25.22.37:8000/docs 超时

**原因和解决：**
- ❌ Nginx 或 FastAPI 未启动
- ✓ 检查容器：`docker-compose -f docker-compose.prod.yml ps`
- ✓ 查看 Nginx 日志：`docker-compose -f docker-compose.prod.yml logs nginx`

---

## 📚 后续你需要知道的

### 每天需要做的

无需手动操作。所有容器会自动重启和管理。

### 每周需要做的

备份数据库（以防万一）：

```bash
cd /opt/pixel/service
docker-compose -f docker-compose.prod.yml exec -T postgres pg_dump -U postgres pixel_db | gzip > backup_$(date +%Y%m%d).sql.gz
```

### 需要更新代码时

```bash
cd /opt/pixel
git pull origin main
cd service
docker-compose -f docker-compose.prod.yml build api
docker-compose -f docker-compose.prod.yml up -d api
```

### 需要查看日志时

```bash
cd /opt/pixel/service
docker-compose -f docker-compose.prod.yml logs -f api
```

---

## 🎉 恭喜！

你已经成功将后端应用部署到腾讯云了！

**现在你可以：**
- ✅ 访问 API 文档：http://118.25.22.37:8000/docs
- ✅ 测试 API 端点
- ✅ 监控后台任务：http://118.25.22.37:5555
- ✅ 定期备份数据
- ✅ 更新应用代码

**下一步建议：**
1. 配置域名和 HTTPS（可选）
2. 配置监控告警（推荐）
3. 设置定期备份（重要）
4. 部署前端应用（web 项目）

---

## 📞 需要帮助？

查看详细文档：

| 文档 | 用途 |
|------|------|
| `DEPLOYMENT_CHECKLIST.md` | 核查清单（确保没遗漏） |
| `TENCENT_CLOUD_QUICKSTART.md` | 常用命令速查 |
| `DEPLOYMENT.md` | 完整参考（深入了解） |
| `DEPLOYMENT_SUMMARY.md` | 架构概览 |

---

**版本**：v1.0  
**最后更新**：2026-03-31  
**难度级别**：⭐ 入门（无需编程知识）  
**预计耗时**：35 分钟（首次）
