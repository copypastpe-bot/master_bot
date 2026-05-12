#!/bin/bash
set -e

SERVER="deploy@75.119.153.118"
STATIC_DIR="/var/www/abooking.org"

echo "=== Creating static dir on server ==="
ssh $SERVER "sudo mkdir -p $STATIC_DIR && sudo chown \$(whoami):\$(whoami) $STATIC_DIR"

echo "=== Uploading landing to server ==="
rsync -avz --delete --exclude='.DS_Store' \
  --chmod=D755,F644 \
  landing/ $SERVER:$STATIC_DIR/

echo "=== Uploading nginx config ==="
scp nginx/landing.conf $SERVER:/tmp/landing.conf
ssh $SERVER "sudo cp /tmp/landing.conf /etc/nginx/sites-available/landing.conf && \
             sudo ln -sf /etc/nginx/sites-available/landing.conf /etc/nginx/sites-enabled/landing.conf && \
             sudo nginx -t"

echo "=== Reloading nginx ==="
ssh $SERVER "sudo systemctl reload nginx"

echo ""
echo "=== Done! ==="
echo "Landing: https://abooking.org"
echo "Privacy: https://abooking.org/privacy.html"
