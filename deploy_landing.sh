#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER="deploy@75.119.153.118"
STATIC_DIR="/var/www/abooking.org"

echo "=== Building landing ==="
cd "$SCRIPT_DIR/landing-v2"
npm run build

echo "=== Creating static dir on server ==="
ssh $SERVER "sudo mkdir -p $STATIC_DIR && sudo chown \$(whoami):\$(whoami) $STATIC_DIR"

echo "=== Uploading landing to server ==="
rsync -avz --delete --exclude='.DS_Store' dist/ $SERVER:$STATIC_DIR/

echo "=== Normalizing perms on server ==="
ssh $SERVER "find $STATIC_DIR -type d -exec chmod 755 {} \; && find $STATIC_DIR -type f -exec chmod 644 {} \;"

echo "=== Uploading nginx config ==="
scp "$SCRIPT_DIR/nginx/landing.conf" $SERVER:/tmp/landing.conf
ssh $SERVER "sudo cp /tmp/landing.conf /etc/nginx/sites-available/landing.conf && \
             sudo ln -sf /etc/nginx/sites-available/landing.conf /etc/nginx/sites-enabled/landing.conf && \
             sudo nginx -t"

echo "=== Reloading nginx ==="
ssh $SERVER "sudo systemctl reload nginx"

echo ""
echo "=== Done! ==="
echo "Landing RU: https://abooking.org"
echo "Landing EN: https://abooking.org/en/"
echo "Privacy:    https://abooking.org/privacy.html"
echo "Robots:     https://abooking.org/robots.txt"
echo "Sitemap:    https://abooking.org/sitemap.xml"
