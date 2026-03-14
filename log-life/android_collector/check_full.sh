#!/data/data/com.termux/files/usr/bin/bash

echo "================================================"
echo "   ПОЛНАЯ ПРОВЕРКА ПРОЕКТА LOG-LIFE"
echo "   $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================"

# --- 1. ПРОЦЕССЫ ---
echo ""
echo "[ 1 ] ПРОЦЕССЫ"
C1=$(pgrep -f "collector\.py" | grep -v collector_db | wc -l)
C2=$(pgrep -f "collector_db\.py" | wc -l)
CW=$(pgrep -f "watcher\.sh" | wc -l)

[ $C1 -gt 0 ] && echo "  ✅ collector.py      — работает" || echo "  ❌ collector.py      — НЕ РАБОТАЕТ"
[ $C2 -gt 0 ] && echo "  ✅ collector_db.py   — работает" || echo "  ❌ collector_db.py   — НЕ РАБОТАЕТ"
[ $CW -gt 0 ] && echo "  ✅ watcher.sh        — работает" || echo "  ⚠️  watcher.sh        — не запущен"

# --- 2. ФАЙЛЫ ---
echo ""
echo "[ 2 ] ФАЙЛЫ ПРОЕКТА"
FILES="collector.py collector_db.py view_logs.py life_log.txt life_log_encrypted.db secret.key"
for f in $FILES; do
    if [ -f "$f" ]; then
        SIZE=$(du -h "$f" 2>/dev/null | cut -f1)
        echo "  ✅ $f ($SIZE)"
    else
        echo "  ❌ $f — ОТСУТСТВУЕТ"
    fi
done

# --- 3. СВЕЖЕСТЬ ЛОГОВ ---
echo ""
echo "[ 3 ] СВЕЖЕСТЬ ЛОГОВ"
if [ -f life_log.txt ]; then
    LAST=$(stat -c %Y life_log.txt 2>/dev/null)
    NOW=$(date +%s)
    DIFF=$((NOW - LAST))
    if [ $DIFF -lt 120 ]; then
        echo "  ✅ life_log.txt — свежий (${DIFF} сек назад)"
    elif [ $DIFF -lt 300 ]; then
        echo "  ⚠️  life_log.txt — ${DIFF} сек назад (возможна задержка)"
    else
        echo "  ❌ life_log.txt — устарел (${DIFF} сек назад)"
    fi
    echo "  Последняя запись: $(tail -1 life_log.txt)"
fi

# --- 4. БАЗА ДАННЫХ ---
echo ""
echo "[ 4 ] БАЗА ДАННЫХ"
if [ -f life_log_encrypted.db ]; then
    DB_SIZE=$(du -h life_log_encrypted.db | cut -f1)
    echo "  ✅ БД существует ($DB_SIZE)"
    TOTAL=$(python -c "
import sqlite3
try:
    conn = sqlite3.connect('life_log_encrypted.db')
    n = conn.execute('SELECT COUNT(*) FROM events').fetchone()[0]
    print(n)
    conn.close()
except:
    print('error')
" 2>/dev/null)
    echo "  📊 Всего записей: $TOTAL"
else
    echo "  ❌ БД не найдена"
fi

# --- 5. РАСШИФРОВКА ---
echo ""
echo "[ 5 ] РАСШИФРОВКА (последние 3 записи)"
python view_logs.py 3 2>/dev/null || echo "  ❌ Ошибка расшифровки"

# --- 6. БАТАРЕЯ ---
echo ""
echo "[ 6 ] БАТАРЕЯ"
BATT=$(termux-battery-status 2>/dev/null)
if [ -n "$BATT" ]; then
    PCT=$(echo $BATT | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('percentage','?'))" 2>/dev/null)
    STAT=$(echo $BATT | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','?'))" 2>/dev/null)
    TEMP=$(echo $BATT | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('temperature','?'))" 2>/dev/null)
    echo "  🔋 Заряд: ${PCT}% | Статус: $STAT | Темп: ${TEMP}°C"
    [ "$PCT" -lt 20 ] 2>/dev/null && echo "  ⚠️  Низкий заряд! Зарядись."
else
    echo "  ❌ Нет данных батареи"
fi

# --- 7. ИНТЕРНЕТ ---
echo ""
echo "[ 7 ] ИНТЕРНЕТ"
ping -c 1 -W 3 8.8.8.8 > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "  ✅ Интернет — онлайн"
else
    echo "  ❌ Интернет — офлайн"
fi

# --- 8. АВТОЗАПУСК ---
echo ""
echo "[ 8 ] АВТОЗАПУСК"
BOOT=~/.termux/boot/start-loggers.sh
if [ -f "$BOOT" ]; then
    echo "  ✅ Автозапуск настроен ($BOOT)"
else
    echo "  ❌ Автозапуск НЕ настроен"
fi

# --- 9. МЕСТО НА ДИСКЕ ---
echo ""
echo "[ 9 ] МЕСТО НА ДИСКЕ"
df -h /data/data/com.termux 2>/dev/null | tail -1 | awk '{print "  💾 Размер:"$2" Использовано:"$3" Свободно:"$4" ("$5")"}'

# --- 10. GIT ---
echo ""
echo "[ 10 ] GIT"
if [ -d ~/bratuha/.git ] || [ -d ~/bratuha/log-life/.git ]; then
    cd ~/bratuha 2>/dev/null || cd ~/bratuha/log-life 2>/dev/null
    BRANCH=$(git branch --show-current 2>/dev/null)
    LAST_COMMIT=$(git log -1 --format="%cr: %s" 2>/dev/null)
    CHANGES=$(git status --short 2>/dev/null | wc -l)
    echo "  ✅ Git репозиторий найден"
    echo "  🌿 Ветка: $BRANCH"
    echo "  📝 Последний коммит: $LAST_COMMIT"
    [ $CHANGES -gt 0 ] && echo "  ⚠️  Несохранённых изменений: $CHANGES файлов" || echo "  ✅ Все изменения закоммичены"
    cd ~/bratuha/log-life/android_collector 2>/dev/null
else
    echo "  ⚠️  Git не инициализирован"
fi

# --- ИТОГ ---
echo ""
echo "================================================"
echo "   ИТОГ"
echo "================================================"
ERRORS=0
[ $C1 -eq 0 ] && ERRORS=$((ERRORS+1))
[ $C2 -eq 0 ] && ERRORS=$((ERRORS+1))

if [ $ERRORS -eq 0 ]; then
    echo "  ✅ Система работает нормально"
    echo "  📱 Данные собираются каждую минуту"
else
    echo "  ❌ Найдено проблем: $ERRORS"
    echo "  🔧 Запусти: nohup python collector.py > collector_out.log 2>&1 &"
    echo "  🔧 Запусти: nohup python collector_db.py > collector_db_out.log 2>&1 &"
fi
echo "================================================"
