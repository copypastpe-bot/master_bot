#!/bin/bash

PROJECT_DIR="/Users/evgenijpastusenko/Projects/Master_bot"
ENV_FILE="$PROJECT_DIR/.env"
LOG_DIR="$PROJECT_DIR/logs"
MASTER_LOG="$LOG_DIR/master_bot.log"
CLIENT_LOG="$LOG_DIR/client_bot.log"

cd "$PROJECT_DIR"

echo ""
echo "📁 Проект: $PROJECT_DIR"
echo "🌱 Env: $ENV_FILE"
echo "📄 Логи: $LOG_DIR"
echo ""

# Create logs directory if not exists
mkdir -p "$LOG_DIR"

# Stop master bot
MASTER_PID=$(pgrep -f "run_master.py" 2>/dev/null)
if [ -n "$MASTER_PID" ]; then
    kill $MASTER_PID 2>/dev/null
    echo "✅ Master bot остановлен (PID: $MASTER_PID)"
else
    echo "⚪ Master bot не был запущен"
fi

# Stop client bot
CLIENT_PID=$(pgrep -f "run_client.py" 2>/dev/null)
if [ -n "$CLIENT_PID" ]; then
    kill $CLIENT_PID 2>/dev/null
    echo "✅ Client bot остановлен (PID: $CLIENT_PID)"
else
    echo "⚪ Client bot не был запущен"
fi

sleep 1

echo ""
echo "🚀 Запускаю ботов..."
echo ""

# Start master bot
nohup python3 run_master.py > "$MASTER_LOG" 2>&1 &
NEW_MASTER_PID=$!
echo "✅ Master bot запущен. PID: $NEW_MASTER_PID"
echo "   Лог: $MASTER_LOG"

# Start client bot
nohup python3 run_client.py > "$CLIENT_LOG" 2>&1 &
NEW_CLIENT_PID=$!
echo "✅ Client bot запущен. PID: $NEW_CLIENT_PID"
echo "   Лог: $CLIENT_LOG"

echo ""
echo "📊 Для просмотра логов:"
echo "   tail -f $MASTER_LOG"
echo "   tail -f $CLIENT_LOG"
echo ""
