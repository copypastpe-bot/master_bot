#!/bin/bash
set -e
echo "Building Mini App..."
cd miniapp
npm install
npm run build
echo "Build complete: miniapp/dist/"
