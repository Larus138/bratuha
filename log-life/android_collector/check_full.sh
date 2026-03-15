#!/data/data/com.termux/files/usr/bin/bash
cd ~/bratuha/log-life/android_collector

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║         БРАТУХА — СТАТУС СИСТЕМЫ        ║"
echo "║  $(date '+%Y-%m-%d  %H:%M:%S')                  ║"
echo "╚══════════════════════════════════════════╝"

# ── ПРОЦЕССЫ ─────────────────────────────────
echo ""
echo "[ ПРОЦЕССЫ ]"
C1=$(pgrep -f "collector_db" | wc -l)
C2=$(pgrep -f "watcher.sh" | wc -l)
C3=$(pgrep -f "crond" | wc -l)
C4=$(pgrep -f "tg_" | wc -l)

[ $C1 -gt 0 ] && echo "  ✅ Сбор данных      — работает" || echo "  ❌ Сбор данных      — НЕ РАБОТАЕТ"
[ $C2 -gt 0 ] && echo "  ✅ Мониторинг       — работает" || echo "  ❌ Мониторинг       — НЕ РАБОТАЕТ"
[ $C3 -gt 0 ] && echo "  ✅ Планировщик      — работает" || echo "  ❌ Планировщик      — НЕ РАБОТАЕТ"
[ $C4 -gt 0 ] && echo "  ⚠️  Telegram скрипт  — запущен сейчас" || echo "  ✅ Telegram         — в расписании (23:00)"

# ── ДАННЫЕ ───────────────────────────────────
echo ""
echo "[ БАЗА ДАННЫХ ]"
TOTAL=$(python -c "
import sqlite3
conn = sqlite3.connect('life_log_encrypted.db')
print(conn.execute('SELECT COUNT(*) FROM events').fetchone()[0])
conn.close()
" 2>/dev/null)
SIZE=$(du -h life_log_encrypted.db 2>/dev/null | cut -f1)
TYPES=$(python -c "
import sqlite3
conn = sqlite3.connect('life_log_encrypted.db')
n = conn.execute('SELECT COUNT(DISTINCT event_type) FROM events').fetchone()[0]
print(n)
conn.close()
" 2>/dev/null)
echo "  📊 Записей         : $TOTAL"
echo "  💾 Размер          : $SIZE"
echo "  🗂️  Типов данных    : $TYPES"

# ── СВЕЖЕСТЬ ─────────────────────────────────
echo ""
echo "[ СВЕЖЕСТЬ ДАННЫХ ]"
LAST=$(python -c "
import sqlite3, datetime
conn = sqlite3.connect('life_log_encrypted.db')
ts = conn.execute(\"SELECT MAX(timestamp) FROM events WHERE event_type='battery'\").fetchone()[0]
if ts:
    t = datetime.datetime.strptime(ts[:19], '%Y-%m-%d %H:%M:%S')
    diff = int((datetime.datetime.now() - t).total_seconds())
    print(diff)
conn.close()
" 2>/dev/null)

if [ -n "$LAST" ]; then
    if [ $LAST -lt 120 ]; then
        echo "  ✅ Последняя запись : ${LAST} сек назад — свежо"
    elif [ $LAST -lt 300 ]; then
        echo "  ⚠️  Последняя запись : ${LAST} сек назад — задержка"
    else
        echo "  ❌ Последняя запись : ${LAST} сек назад — проблема"
    fi
fi

# ── БАТАРЕЯ ──────────────────────────────────
echo ""
echo "[ БАТАРЕЯ ]"
BATT=$(termux-battery-status 2>/dev/null)
if [ -n "$BATT" ]; then
    PCT=$(echo $BATT | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('percentage','?'))" 2>/dev/null)
    STAT=$(echo $BATT | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','?'))" 2>/dev/null)
    TEMP=$(echo $BATT | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('temperature','?'))" 2>/dev/null)
    echo "  🔋 Заряд           : ${PCT}%  ${STAT}  ${TEMP}°C"
    [ "$PCT" -lt 20 ] 2>/dev/null && echo "  ⚠️  Низкий заряд — зарядись!"
fi

# ── ИНТЕРНЕТ ─────────────────────────────────
echo ""
echo "[ СЕТЬ ]"
ping -c 1 -W 3 8.8.8.8 > /dev/null 2>&1 && echo "  ✅ Интернет        — онлайн" || echo "  ❌ Интернет        — офлайн"

# ── ДИСК ─────────────────────────────────────
echo ""
echo "[ ДИСК ]"
df -h /data/data/com.termux 2>/dev/null | tail -1 | awk '{print "  💾 " $3 " из " $2 " использовано (" $5 ")"}'

# ── GIT ──────────────────────────────────────
echo ""
echo "[ GIT ]"
cd ~/bratuha 2>/dev/null
CHANGES=$(git status --short 2>/dev/null | wc -l)
LAST_COMMIT=$(git log -1 --format="%cr" 2>/dev/null)
[ $CHANGES -gt 0 ] && echo "  ⚠️  Несохранённых изменений: $CHANGES" || echo "  ✅ Всё сохранено"
echo "  📝 Последний коммит: $LAST_COMMIT"
cd ~/bratuha/log-life/android_collector 2>/dev/null

# ── ИТОГ ─────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════╗"
ERRORS=0
[ $C1 -eq 0 ] && ERRORS=$((ERRORS+1))
[ $C2 -eq 0 ] && ERRORS=$((ERRORS+1))
[ $C3 -eq 0 ] && ERRORS=$((ERRORS+1))
if [ $ERRORS -eq 0 ]; then
    echo "║  ✅ Система работает нормально           ║"
else
    echo "║  ❌ Проблем найдено: $ERRORS                      ║"
fi
echo "║  Команды: dashboard | analyze | note    ║"
echo "╚══════════════════════════════════════════╝"
echo ""
