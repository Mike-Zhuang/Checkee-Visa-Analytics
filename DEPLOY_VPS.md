# VPS 部署说明（Nginx + systemd）

## 1. 前置环境

- Ubuntu 22.04+
- Python 3.11+
- Node.js 20+
- pnpm（推荐）或 npm
- nginx

## 2. 目录约定

- 应用根目录：`/opt/checkee`
- 后端服务：`checkee-backend.service`
- 前端静态目录：`/var/www/checkee/frontend/dist`

## 3. 配置环境变量

复制模板并填写：

```bash
sudo mkdir -p /opt/checkee/deploy/env
sudo cp /opt/checkee/deploy/env/backend.env.example /opt/checkee/deploy/env/backend.env
```

重点修改：

- `CHECKEE_CORS_ALLOW_ORIGINS`
- `CHECKEE_DATA_DIR`
- `CHECKEE_APP_VERSION`

## 4. 执行部署脚本

```bash
cd /opt/checkee
sudo bash deploy/scripts/deploy-backend.sh
```

## 5. 安装 Nginx 配置

```bash
sudo cp /opt/checkee/deploy/nginx/checkee.conf /etc/nginx/sites-available/checkee.conf
sudo ln -sf /etc/nginx/sites-available/checkee.conf /etc/nginx/sites-enabled/checkee.conf
sudo nginx -t
sudo systemctl reload nginx
```

## 6. 健康检查

```bash
curl -sS http://127.0.0.1:8000/api/v1/health
curl -sS http://127.0.0.1/api/v1/health
```

## 7. 回滚策略

- 保留上一版代码目录（建议按时间戳备份）
- 回滚时恢复旧目录并重启服务：

```bash
sudo systemctl restart checkee-backend.service
```

## 8. 建议的运维动作

- 打开 systemd 自恢复（模板已启用 `Restart=always`）
- 配置日志轮转（journald / rsyslog）
- 定期备份 `backend/data`
- 将域名接入 HTTPS（建议 certbot）
