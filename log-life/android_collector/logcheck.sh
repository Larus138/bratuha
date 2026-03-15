#!/data/data/com.termux/files/usr/bin/bash
cd ~/bratuha/log-life/android_collector
echo "=== СТАТУС $(date '+%Y-%m-%d %H:%M:%S') ==="
echo ""
echo "--- Процессы ---"
ps aux | grep -E "collector_db|watcher" | grep -v grep
echo ""
echo "--- БД последние 5 ---"
python view_logs.py 5
