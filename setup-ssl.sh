#!/usr/bin/env bash
# SSL setup for KSeF Integration API via Nginx + Let's Encrypt (Certbot)
# Supports both Docker Compose and systemd deployments.
#
# Usage:
#   sudo ./setup-ssl.sh --type docker   --domain api.example.com [--port 5000]
#   sudo ./setup-ssl.sh --type systemd  --domain api.example.com [--port 5000]
#
# Options:
#   --type    docker | systemd  (required)
#   --domain  public domain pointing to this server (required)
#   --port    service port on the host (default: 5000)
#   --email   e-mail for Let's Encrypt (default: admin@<domain>)

set -euo pipefail

# ── defaults ──────────────────────────────────────────────────────────────────
TYPE=""
DOMAIN=""
PORT="5000"
EMAIL=""

# ── parse args ────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --type)   TYPE="$2";   shift 2 ;;
    --domain) DOMAIN="$2"; shift 2 ;;
    --port)   PORT="$2";   shift 2 ;;
    --email)  EMAIL="$2";  shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

EMAIL="${EMAIL:-admin@${DOMAIN}}"

# ── validation ────────────────────────────────────────────────────────────────
if [[ -z "$TYPE" || -z "$DOMAIN" ]]; then
  echo "Usage: sudo $0 --type docker|systemd --domain api.example.com [--port 5000] [--email admin@example.com]"
  exit 1
fi

if [[ "$EUID" -ne 0 ]]; then
  echo "Run as root: sudo $0 $*"
  exit 1
fi

# ── check service is reachable ────────────────────────────────────────────────
echo "==> Checking service on port ${PORT}"

if [[ "$TYPE" == "docker" ]]; then
  if ! docker ps --format '{{.Ports}}' | grep -q "0.0.0.0:${PORT}->"; then
    echo "ERROR: No Docker container found listening on host port ${PORT}."
    echo "Start the service first:"
    echo "  docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d"
    exit 1
  fi
  echo "  Docker container on :${PORT} — OK"

elif [[ "$TYPE" == "systemd" ]]; then
  if ! systemctl is-active --quiet ksef-encryptor.service; then
    echo "ERROR: systemd service ksef-encryptor.service is not running."
    echo "Start it with: sudo systemctl start ksef-encryptor.service"
    exit 1
  fi
  echo "  systemd service ksef-encryptor.service — OK"

else
  echo "ERROR: --type must be 'docker' or 'systemd'"
  exit 1
fi

# ── install nginx + certbot ───────────────────────────────────────────────────
echo "==> Installing Nginx and Certbot"
apt-get update -q
apt-get install -y --no-install-recommends nginx certbot python3-certbot-nginx

# ── nginx config ──────────────────────────────────────────────────────────────
echo "==> Writing Nginx config for ${DOMAIN}"
cat > "/etc/nginx/sites-available/${DOMAIN}" <<EOF
server {
    listen 80;
    server_name ${DOMAIN};

    location / {
        proxy_pass         http://127.0.0.1:${PORT};
        proxy_set_header   Host              \$host;
        proxy_set_header   X-Real-IP         \$remote_addr;
        proxy_set_header   X-Forwarded-For   \$proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
        proxy_buffering    off;
    }
}
EOF

ln -sf "/etc/nginx/sites-available/${DOMAIN}" "/etc/nginx/sites-enabled/${DOMAIN}"
nginx -t
systemctl reload nginx

# ── certbot ───────────────────────────────────────────────────────────────────
echo "==> Obtaining Let's Encrypt certificate for ${DOMAIN}"
certbot --nginx -d "${DOMAIN}" --agree-tos --redirect --email "${EMAIL}" --non-interactive

# ── summary ───────────────────────────────────────────────────────────────────
echo ""
echo "Done."
echo "  Service : https://${DOMAIN}"
echo "  Type    : ${TYPE}"
echo "  Backend : localhost:${PORT}"
echo ""
echo "Auto-renewal via systemd timer — verify with:"
echo "  systemctl status certbot.timer"
echo "  certbot renew --dry-run"
