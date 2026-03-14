#!/data/data/com.termux/files/usr/bin/bash
LOG_FILE="watcher.log"
NOTIFIED="/dev/shm/watcher_notified"
STALE="/dev/shm/stale_log"

check() {
    proc=$(pgrep -f "python.*collector" | wc -l)
    procdb=$(pgrep -f "python.*collector_db" | wc -l)
    if [ $proc -eq 0 ] || [ $procdb -eq 0 ]; then
        [ ! -f "$NOTIFIED" ] && termux-notification --id loglife --title "⚠️ LogLife" \
            --content "collector.py: $proc, collector_db.py: $procdb" --priority high --vibrate 500 && \
            touch "$NOTIFIED" && echo "$(date): Уведомление" >> "$LOG_FILE"
    else
        rm -f "$NOTIFIED"
    fi
    if [ -f life_log.txt ]; then
        last=$(stat -c %Y life_log.txt)
        now=$(date +%s)
        if [ $((now - last)) -gt 180 ]; then
            [ ! -f "$STALE" ] && termux-notification --id loglife_stale --title "⚠️ LogLife" \
                --content "Лог устарел" --priority high --vibrate 500 && touch "$STALE"
        else
            rm -f "$STALE"
        fi
    fi
}
while true; do check; sleep 120; done
