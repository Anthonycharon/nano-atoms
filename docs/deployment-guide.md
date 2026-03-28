# Nano Atoms 部署指引

## 1. 目标架构
推荐单机部署：

- `frontend`：Next.js，监听 `127.0.0.1:3000`
- `backend`：FastAPI，监听 `127.0.0.1:8000`
- `nginx`：对外暴露 `80/443`
- `systemd`：托管前后端进程

对外统一使用一个域名，例如 `https://nano-atoms.example.com`：

- `/` -> 前端
- `/api/*`、`/ws/*`、`/uploads/*`、`/health` -> 后端

## 2. 服务器要求
- Ubuntu 22.04/24.04
- Python 3.12+
- Node.js 20+
- Nginx
- Git

安装基础依赖：

```bash
sudo apt update
sudo apt install -y git nginx python3 python3-venv python3-pip curl
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

## 3. 拉取代码

```bash
cd /opt
sudo git clone https://github.com/Anthonycharon/nano-atoms.git
sudo chown -R $USER:$USER /opt/nano-atoms
cd /opt/nano-atoms
git checkout dev-1.1.0
```

## 4. 后端部署

### 4.1 安装依赖

```bash
cd /opt/nano-atoms/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

### 4.2 配置环境变量
复制并编辑：

```bash
cp .env.example .env
nano .env
```

至少需要配置：

```env
DATABASE_URL=sqlite:///./nano_atoms.db
SECRET_KEY=替换成32位以上随机字符串

OPENAI_API_KEY=你的主模型Key
OPENAI_BASE_URL=你的主模型Base URL
OPENAI_MODEL=你的主模型名
OPENAI_TIMEOUT_SECONDS=1200
SITE_CODEGEN_INITIAL_TIMEOUT_SECONDS=900
SITE_CODEGEN_RETRY_TIMEOUT_SECONDS=600
SITE_CODEGEN_FULL_TIMEOUT_SECONDS=1200

OPENAI_IMAGE_API_KEY=你的生图Key
OPENAI_IMAGE_BASE_URL=你的生图Base URL
OPENAI_IMAGE_MODEL=你的生图模型名
OPENAI_IMAGE_ENABLED=true

SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USERNAME=你的QQ邮箱@qq.com
SMTP_PASSWORD=你的QQ邮箱SMTP授权码
SMTP_FROM_EMAIL=你的QQ邮箱@qq.com
SMTP_FROM_NAME=Nano Atoms
SMTP_USE_TLS=false
SMTP_USE_SSL=true

FRONTEND_URL=https://nano-atoms.example.com
PUBLIC_BACKEND_URL=https://nano-atoms.example.com
UPLOAD_DIR=./uploads
```

说明：
- `SECRET_KEY` 必须自己替换。
- `SMTP_PASSWORD` 不是 QQ 登录密码，而是 QQ 邮箱 SMTP 授权码。
- `PUBLIC_BACKEND_URL` 必须是外网可访问地址，否则上传资源 URL 会错误。

### 4.3 本地验证

```bash
source /opt/nano-atoms/backend/.venv/bin/activate
cd /opt/nano-atoms/backend
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

确认：

```bash
curl http://127.0.0.1:8000/health
```

## 5. 前端部署

### 5.1 安装依赖并构建

```bash
cd /opt/nano-atoms/frontend
npm install
```

创建生产环境变量：

```bash
cat > /opt/nano-atoms/frontend/.env.production <<'EOF'
NEXT_PUBLIC_API_URL=https://nano-atoms.example.com
NEXT_PUBLIC_WS_URL=wss://nano-atoms.example.com
EOF
```

然后构建：

```bash
cd /opt/nano-atoms/frontend
npm run build
```

本地验证：

```bash
npm run start -- --hostname 127.0.0.1 --port 3000
```

## 6. systemd 服务

### 6.1 后端服务
创建 `/etc/systemd/system/nano-atoms-backend.service`：

```ini
[Unit]
Description=Nano Atoms Backend
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/opt/nano-atoms/backend
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/nano-atoms/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 6.2 前端服务
创建 `/etc/systemd/system/nano-atoms-frontend.service`：

```ini
[Unit]
Description=Nano Atoms Frontend
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/opt/nano-atoms/frontend
Environment=NODE_ENV=production
ExecStart=/usr/bin/npm run start -- --hostname 127.0.0.1 --port 3000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 6.3 启动服务

```bash
sudo systemctl daemon-reload
sudo systemctl enable nano-atoms-backend nano-atoms-frontend
sudo systemctl start nano-atoms-backend nano-atoms-frontend
sudo systemctl status nano-atoms-backend nano-atoms-frontend
```

## 7. Nginx 反向代理
创建 `/etc/nginx/sites-available/nano-atoms`：

```nginx
server {
    listen 80;
    server_name nano-atoms.example.com;

    client_max_body_size 30m;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /uploads/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

启用站点：

```bash
sudo ln -s /etc/nginx/sites-available/nano-atoms /etc/nginx/sites-enabled/nano-atoms
sudo nginx -t
sudo systemctl reload nginx
```

## 8. HTTPS
推荐 Certbot：

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d nano-atoms.example.com
```

签发完成后，前端 WebSocket 地址必须保持 `wss://`。

## 9. 首次上线检查

```bash
curl https://nano-atoms.example.com/health
```

浏览器检查：
- 首页可打开
- 注册页能收到邮箱验证码
- 登录正常
- Dashboard 正常
- 创建项目并生成应用
- 预览、文件树、发布页正常

调试入口：
- `https://nano-atoms.example.com/debug/email-test`
- `https://nano-atoms.example.com/debug/image-test`

## 10. 日志与排障

查看服务日志：

```bash
sudo journalctl -u nano-atoms-backend -f
sudo journalctl -u nano-atoms-frontend -f
```

查看 Nginx 日志：

```bash
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

常见问题：
- 注册收不到验证码：先检查 QQ 邮箱 SMTP 配置，再测 `/debug/email-test`
- 图片不生成：检查生图模型配置，再测 `/debug/image-test`
- WebSocket 不通：确认 Nginx 的 `/ws/` 已配置 `Upgrade/Connection`
- 上传图片打不开：确认 `PUBLIC_BACKEND_URL` 是公网域名
- 服务启动失败：确认 `frontend/.env.production`、`backend/.env` 已正确配置

## 11. 更新发布

```bash
cd /opt/nano-atoms
git pull origin dev-1.1.0

cd /opt/nano-atoms/backend
source .venv/bin/activate
pip install -r requirements.txt

cd /opt/nano-atoms/frontend
npm install
npm run build

sudo systemctl restart nano-atoms-backend nano-atoms-frontend
```

## 12. 生产建议
- 当前默认数据库是 SQLite，适合单机和演示环境；正式生产建议迁移到 MySQL/PostgreSQL。
- 不要把 `backend/.env` 提交到 Git。
- 为 `uploads/` 和 `nano_atoms.db` 做定期备份。
- 如果访问量增大，再考虑把前后端拆到容器或独立服务。
