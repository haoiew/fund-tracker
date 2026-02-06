# Oracle Cloud 免费服务器完整部署教程

## 🎯 教程概述

本教程将指导你使用 Oracle Cloud 永久免费套餐（2台 AMD 1核1G VM）部署基金跟踪器后端服务。

**免费资源额度：**
- 2台 AMD 虚拟机（1核1G内存）**永久免费**
- 200GB 块存储
- 10TB 出站流量/月

---

## 第一步：注册 Oracle Cloud 账号

### 1.1 访问官网注册

1. 打开 https://www.oracle.com/cloud/free/
2. 点击 **"Start for free"**
3. 填写注册信息：
   - 国家/地区：选择 **"China"** 或你所在地区
   - 姓名：真实姓名
   - 邮箱：有效邮箱（需要验证）
   - 手机号：需要接收验证码

### 1.2 验证身份

1. 邮箱验证：查收邮件点击验证链接
2. 手机验证：接收短信验证码
3. **重要**：需要绑定支付方式（信用卡或借记卡）
   - 仅用于验证身份，**不会扣费**
   - 支持 Visa、MasterCard
   - 部分国内银行卡可能不支持，可尝试使用虚拟信用卡

### 1.3 登录控制台

注册完成后，访问 https://cloud.oracle.com 登录控制台

---

## 第二步：创建 VM 实例

### 2.1 进入计算实例页面

1. 登录控制台后，点击左上角 **"导航菜单"** (三条横线)
2. 选择 **"计算"** → **"实例"**
3. 点击 **"创建实例"**

### 2.2 配置实例信息

**名称**: `fundtracker-server`

** compartment**: 保持默认（根 compartment）

**放置**: 
- 可用性域：选择任意一个（如 AD-1）

**映像和形状**:
- 点击 **"更改映像"**
- 选择 **"Oracle Linux"** 或 **"Canonical Ubuntu"**（推荐 Ubuntu 22.04）
- 点击 **"更改形状"**
- 选择 **"VM.Standard.E2.1.Micro"**（这是免费套餐）

**网络**:
- 虚拟云网络：选择默认 VCN 或创建新的
- 子网：选择公共子网
- **分配公共 IP 地址**: 勾选 ✓

**添加 SSH 密钥**:
- 选择 **"生成新的密钥对"** 或 **"上传公共密钥"**
- 如果生成新的，下载私钥文件（`.key`）保存好

**启动卷**:
- 引导卷大小：50GB（免费额度内）

### 2.3 创建实例

点击 **"创建"**，等待实例状态变为 **"运行中"**（约1-2分钟）

### 2.4 记录连接信息

创建完成后，记录以下信息：
- **公共 IP 地址**: 如 `132.145.123.45`
- **SSH 密钥**: 下载的私钥文件路径

---

## 第三步：配置安全组（开放端口）

### 3.1 进入安全列表

1. 导航菜单 → **"网络"** → **"虚拟云网络"**
2. 点击你的 VCN 名称
3. 在左侧选择 **"安全列表"**
4. 点击 **"Default Security List"** 或你的安全列表

### 3.2 添加入站规则

点击 **"添加入站规则"**，添加以下规则：

| 状态 | 源类型 | 源 CIDR | IP 协议 | 目标端口范围 | 描述 |
|------|--------|---------|---------|--------------|------|
| 无状态 | CIDR | 0.0.0.0/0 | TCP | 22 | SSH 访问 |
| 无状态 | CIDR | 0.0.0.0/0 | TCP | 8000 | FastAPI 后端 |
| 无状态 | CIDR | 0.0.0.0/0 | TCP | 5432 | PostgreSQL（可选）|
| 无状态 | CIDR | 0.0.0.0/0 | TCP | 6379 | Redis（可选）|

**注意**: 生产环境建议限制源 IP 范围，不要全部开放

---

## 第四步：连接服务器并安装 Docker

### 4.1 SSH 连接服务器

**Windows (PowerShell)**:
```powershell
# 修改私钥权限（如果是 OpenSSH）
icacls "C:\path\to\your-key.key" /inheritance:r /grant:r "$($env:USERNAME):(R)"

# SSH 连接
ssh -i "C:\path\to\your-key.key" ubuntu@132.145.123.45
```

**Mac/Linux**:
```bash
chmod 600 /path/to/your-key.key
ssh -i /path/to/your-key.key ubuntu@132.145.123.45
```

### 4.2 安装 Docker

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 Docker
sudo apt install -y docker.io docker-compose

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker

# 将当前用户加入 docker 组（免 sudo 使用）
sudo usermod -aG docker $USER

# 重新登录使权限生效
exit
```

重新 SSH 连接后，验证 Docker：
```bash
docker --version
docker-compose --version
```

---

## 第五步：部署基金跟踪器后端

### 5.1 创建项目目录

```bash
mkdir -p ~/fund-tracker
cd ~/fund-tracker
```

### 5.2 创建生产环境 Docker Compose 文件

创建 `docker-compose.prod.yml`：

```bash
cat > docker-compose.prod.yml << 'EOF'
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: fundtracker-postgres
    restart: always
    environment:
      POSTGRES_USER: funduser
      POSTGRES_PASSWORD: your-strong-password-here
      POSTGRES_DB: fundtracker
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - fundtracker-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U funduser -d fundtracker"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: fundtracker-redis
    restart: always
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - fundtracker-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: fundtracker-backend
    restart: always
    environment:
      - DATABASE_URL=postgresql://funduser:your-strong-password-here@postgres:5432/fundtracker
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=your-secret-key-change-this
      - DEBUG=false
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - fundtracker-network
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2

volumes:
  postgres_data:
  redis_data:

networks:
  fundtracker-network:
    driver: bridge
EOF
```

### 5.3 创建后端 Dockerfile

```bash
mkdir -p backend
cat > backend/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
EOF
```

### 5.4 复制后端代码

将本地 `fund-tracker/backend` 目录中的所有文件上传到服务器：

**Windows (PowerShell)**:
```powershell
# 使用 scp 上传
scp -i "C:\path\to\your-key.key" -r "D:\workdir\code\Explore\fund-tracker\backend\*" ubuntu@132.145.123.45:~/fund-tracker/backend/
```

**或使用 Git 克隆**（如果代码已推送到 GitHub）：
```bash
cd ~
git clone https://github.com/yourusername/fund-tracker.git
mv fund-tracker/backend ./backend
```

### 5.5 启动服务

```bash
cd ~/fund-tracker

# 构建并启动
docker-compose -f docker-compose.prod.yml up -d --build

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f

# 等待服务启动完成（约30秒）
```

### 5.6 验证部署

```bash
# 检查容器状态
docker ps

# 测试 API 是否可用
curl http://localhost:8000/api/v1/funds/realtime/000001
```

---

## 第六步：配置域名（可选）

### 6.1 申请免费域名

推荐免费域名服务商：
- **Freenom**: https://www.freenom.com/ (.tk, .ml, .ga 等免费域名)
- **DuckDNS**: https://www.duckdns.org/ (免费二级域名)

### 6.2 配置 DNS

在域名管理后台，添加 A 记录指向你的 Oracle Cloud 公共 IP

### 6.3 安装 Nginx 反向代理（推荐）

```bash
# 在服务器上安装 Nginx
sudo apt install -y nginx

# 创建 Nginx 配置
sudo tee /etc/nginx/sites-available/fundtracker << 'EOF'
server {
    listen 80;
    server_name your-domain.com;  # 替换为你的域名

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
EOF

# 启用配置
sudo ln -s /etc/nginx/sites-available/fundtracker /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 第七步：更新前端 API 地址

### 7.1 修改生产环境配置

编辑本地文件 `fund-tracker/frontend/.env.production`：

```env
# 使用 Oracle Cloud 服务器 IP
VITE_API_BASE_URL=http://132.145.123.45:8000/api/v1

# 或者使用域名（如果配置了）
# VITE_API_BASE_URL=http://your-domain.com/api/v1
```

### 7.2 使用 HBuilderX 打包安卓 APK

1. 打开 HBuilderX
2. 导入 `fund-tracker/frontend` 项目
3. 点击 `发行` → `原生App-云打包`
4. 选择 `Android (apk)`
5. 使用公共测试证书
6. 等待打包完成，下载 APK

---

## 第八步：日常维护

### 查看服务状态
```bash
cd ~/fund-tracker
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f backend
```

### 重启服务
```bash
cd ~/fund-tracker
docker-compose -f docker-compose.prod.yml restart
```

### 更新代码
```bash
cd ~/fund-tracker
# 上传新代码到 backend 目录
docker-compose -f docker-compose.prod.yml up -d --build backend
```

### 备份数据
```bash
# 备份 PostgreSQL
docker exec fundtracker-postgres pg_dump -U funduser fundtracker > backup_$(date +%Y%m%d).sql

# 备份 Redis
docker exec fundtracker-redis redis-cli SAVE
docker cp fundtracker-redis:/data/dump.rdb ./redis_backup_$(date +%Y%m%d).rdb
```

---

## ❓ 常见问题

### Q1: 注册时信用卡验证失败？

**A**: 
- 尝试使用 Visa/MasterCard 信用卡
- 部分国内银行可能不支持，可尝试虚拟信用卡服务
- 确保卡内有少量余额用于验证（会退还）

### Q2: 连接不上服务器？

**A**:
- 检查安全组是否开放 22 端口
- 检查 SSH 密钥权限是否正确（Linux/Mac 需要 600）
- 检查实例是否已启动并分配了公共 IP

### Q3: Docker 启动失败？

**A**:
- 检查端口是否被占用：`sudo netstat -tlnp`
- 查看详细日志：`docker-compose logs`
- 确保内存足够（1G 内存较紧张，建议添加 Swap）

### Q4: 如何添加 Swap 分区？

```bash
# 创建 2G Swap 文件
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 永久生效
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## 📞 技术支持

- Oracle Cloud 文档: https://docs.oracle.com/en-us/iaas/Content/home.htm
- Docker 文档: https://docs.docker.com/
- 项目 Issues: https://github.com/yourusername/fund-tracker/issues
