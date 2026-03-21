#!/bin/bash
set -e

SERVER="deploy@75.119.153.118"
STATIC_DIR="/var/www/app.crmfit.ru"

echo "=== Building Mini App ==="
cd miniapp
npm install --silent
npm run build
cd ..

echo "=== Creating static dir on server ==="
ssh $SERVER "sudo mkdir -p $STATIC_DIR && sudo chown \$(whoami):\$(whoami) $STATIC_DIR"

echo "=== Uploading dist to server ==="
rsync -avz --delete miniapp/dist/ $SERVER:$STATIC_DIR/

echo "=== Uploading nginx config ==="
scp nginx/miniapp.conf $SERVER:/tmp/miniapp.conf
ssh $SERVER "sudo cp /tmp/miniapp.conf /etc/nginx/sites-available/miniapp.conf && \
             sudo ln -sf /etc/nginx/sites-available/miniapp.conf /etc/nginx/sites-enabled/miniapp.conf && \
             sudo nginx -t"

echo "=== Reloading nginx ==="
ssh $SERVER "sudo systemctl reload nginx"

echo ""
echo "=== Done! ==="
echo "Mini App: https://app.crmfit.ru"
echo "API:      https://api.crmfit.ru"
