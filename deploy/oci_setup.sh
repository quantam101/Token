#!/usr/bin/env bash
# TokenForge OCI Always-Free deployment script.
# Run as root on a fresh Ubuntu 22.04 OCI VM (VM.Standard.E2.1.Micro is enough).
#
# Prerequisites you handled manually before running this:
#   1. SSH into the VM as `ubuntu` user
#   2. sudo -i
#   3. Cloned the repo to /opt/tokenforge (see DEPLOY_OCI.md step 4)
#   4. Created /opt/tokenforge/backend/.env from .env.production.template
#
# This script is idempotent — safe to re-run after edits.

set -euo pipefail

DOMAIN="${1:?Usage: $0 <api-domain>   (e.g. api.alreadyherellc.com)}"
APP_DIR="/opt/tokenforge"
BACKEND_DIR="${APP_DIR}/backend"
PY_VER="3.11"

echo "==> [1/9] Updating apt + installing system deps"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
  curl wget gnupg lsb-release ca-certificates \
  python${PY_VER} python${PY_VER}-venv python${PY_VER}-dev \
  build-essential nginx certbot python3-certbot-nginx \
  ufw

echo "==> [2/9] Adding 2 GB swap (E2.1.Micro has 1 GB RAM — Mongo will OOM without swap)"
if [ ! -f /swapfile ]; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "==> [3/9] Installing MongoDB 7.0"
if ! command -v mongod >/dev/null; then
  curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor
  echo "deb [arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg] https://repo.mongodb.org/apt/ubuntu $(lsb_release -cs)/mongodb-org/7.0 multiverse" \
    > /etc/apt/sources.list.d/mongodb-org-7.0.list
  apt-get update -qq
  apt-get install -y -qq mongodb-org
  # Limit cache to 256 MB so Mongo doesn't eat all RAM on a 1 GB box
  sed -i 's|#  engine:|  engine: wiredTiger\n  wiredTiger:\n    engineConfig:\n      cacheSizeGB: 0.25|' /etc/mongod.conf || true
  systemctl enable mongod
  systemctl restart mongod
fi

echo "==> [4/9] Setting up Python virtualenv + deps"
if [ ! -d "${BACKEND_DIR}/.venv" ]; then
  python${PY_VER} -m venv "${BACKEND_DIR}/.venv"
fi
"${BACKEND_DIR}/.venv/bin/pip" install --upgrade pip wheel -q
"${BACKEND_DIR}/.venv/bin/pip" install -r "${BACKEND_DIR}/requirements.txt" -q

echo "==> [5/9] Writing systemd service"
cat > /etc/systemd/system/tokenforge-backend.service <<EOF
[Unit]
Description=TokenForge FastAPI backend
After=network.target mongod.service
Requires=mongod.service

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=${BACKEND_DIR}
EnvironmentFile=${BACKEND_DIR}/.env
ExecStart=${BACKEND_DIR}/.venv/bin/uvicorn server:app --host 0.0.0.0 --port 8001 --workers 1
Restart=always
RestartSec=5
# Memory safeguard — kill + restart if backend exceeds 600MB
MemoryMax=600M

[Install]
WantedBy=multi-user.target
EOF

chown -R ubuntu:ubuntu "${APP_DIR}"
systemctl daemon-reload
systemctl enable tokenforge-backend
systemctl restart tokenforge-backend

echo "==> [6/9] Configuring nginx reverse proxy"
cat > /etc/nginx/sites-available/tokenforge <<EOF
server {
    listen 80;
    server_name ${DOMAIN};
    client_max_body_size 5M;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }
}
EOF

ln -sf /etc/nginx/sites-available/tokenforge /etc/nginx/sites-enabled/tokenforge
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo "==> [7/9] Opening firewall ports (UFW + OCI iptables)"
ufw allow OpenSSH >/dev/null 2>&1 || true
ufw allow 80/tcp >/dev/null 2>&1 || true
ufw allow 443/tcp >/dev/null 2>&1 || true
yes | ufw enable >/dev/null 2>&1 || true
# OCI uses iptables-persistent — open ports there too
iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
netfilter-persistent save >/dev/null 2>&1 || iptables-save > /etc/iptables/rules.v4 2>/dev/null || true

echo "==> [8/9] Provisioning Let's Encrypt SSL"
echo "    (this requires the DNS A record for ${DOMAIN} → this server's IP to already be live)"
certbot --nginx -d "${DOMAIN}" --non-interactive --agree-tos -m dispatch@alreadyherellc.com --redirect

echo "==> [9/9] Done. Health checks:"
sleep 2
systemctl --no-pager status tokenforge-backend | head -6
echo ""
curl -sf "https://${DOMAIN}/api/stats/public" && echo "" || echo "API check FAILED — see: journalctl -u tokenforge-backend -n 50"

echo ""
echo "✅ Deploy complete. Backend live at: https://${DOMAIN}"
echo "   Logs: journalctl -fu tokenforge-backend"
echo "   Restart after .env change: systemctl restart tokenforge-backend"
