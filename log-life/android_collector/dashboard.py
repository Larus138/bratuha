import sqlite3, datetime, os, json
from cryptography.fernet import Fernet

os.chdir(os.path.dirname(os.path.abspath(__file__)))

with open("secret.key", "rb") as f:
    key = f.read()
cipher = Fernet(key)
conn = sqlite3.connect("life_log_encrypted.db")

def decrypt(val):
    try:
        return cipher.decrypt(val).decode()
    except:
        return ""

def get_last(event_type):
    row = conn.execute(
        "SELECT timestamp, value FROM events WHERE event_type=? ORDER BY timestamp DESC LIMIT 1",
        (event_type,)
    ).fetchone()
    if row:
        return row[0], decrypt(row[1])
    return None, None

def get_today(event_type):
    today = datetime.date.today().strftime('%Y-%m-%d')
    rows = conn.execute(
        "SELECT timestamp, value FROM events WHERE event_type=? AND timestamp LIKE ? ORDER BY timestamp",
        (event_type, today+'%')
    ).fetchall()
    return [(r[0], decrypt(r[1])) for r in rows]

def get_last_n(event_type, n=24):
    rows = conn.execute(
        "SELECT timestamp, value FROM events WHERE event_type=? ORDER BY timestamp DESC LIMIT ?",
        (event_type, n)
    ).fetchall()
    return [(r[0], decrypt(r[1])) for r in rows]

now = datetime.datetime.now()
today = datetime.date.today()

print("╔══════════════════════════════════════════════╗")
print("║        БРАТУХА — ДАШБОРД                    ║")
print(f"║  {now.strftime('%Y-%m-%d  %H:%M:%S')}                    ║")
print("╚══════════════════════════════════════════════╝")

# ── БАТАРЕЯ ──────────────────────────────────────
print("\n🔋 БАТАРЕЯ")
ts, val = get_last("battery")
if val:
    print(f"   {val}")
    # График заряда за день
    today_batt = get_today("battery")
    if today_batt:
        levels = []
        for _, v in today_batt:
            try:
                pct = int(v.split('%')[0])
                levels.append(pct)
            except:
                pass
        if levels:
            mini = min(levels)
            maxi = max(levels)
            avg  = sum(levels) // len(levels)
            print(f"   Сегодня: min {mini}% → max {maxi}% → avg {avg}%")

            # Мини график
            step = max(1, len(levels) // 20)
            bar = ""
            for i in range(0, len(levels), step):
                pct = levels[i]
                if pct >= 80: bar += "█"
                elif pct >= 60: bar += "▆"
                elif pct >= 40: bar += "▄"
                elif pct >= 20: bar += "▂"
                else: bar += "▁"
            print(f"   График : {bar}")

# ── СИСТЕМА ───────────────────────────────────────
print("\n⚙️  СИСТЕМА")
_, cpu = get_last("cpu_load")
_, ram = get_last("ram")
_, disk = get_last("disk")
_, uptime = get_last("uptime")
_, inet = get_last("internet")

if cpu:  print(f"   CPU    : {cpu}")
if ram:  print(f"   RAM    : {ram}")
if disk: print(f"   Диск   : {disk}")
if uptime: print(f"   Uptime : {uptime}")
if inet: print(f"   Сеть   : {inet}")

# ── ПОГОДА ───────────────────────────────────────
print("\n🌤️  ПОГОДА ИРКУТСК")
ts, weather = get_last("weather")
if weather:
    print(f"   {weather}")
    if ts:
        t = datetime.datetime.strptime(ts[:19], '%Y-%m-%d %H:%M:%S')
        mins = int((now - t).total_seconds() / 60)
        print(f"   Обновлено {mins} мин назад")

# ── АКТИВНОСТЬ СЕГОДНЯ ───────────────────────────
print("\n📊 АКТИВНОСТЬ СЕГОДНЯ")
today_all = get_today("battery")
records_today = len(today_all)
hours_active = records_today / 60
print(f"   Записей собрано  : {records_today}")
print(f"   Часов активности : {hours_active:.1f}")

# Определяем сейчас заряжается или нет
if today_all:
    _, last_batt = today_all[-1]
    if last_batt:
        if "CHARGING" in last_batt:
            print(f"   Статус           : 🔌 На зарядке")
        else:
            print(f"   Статус           : 📱 Активно используется")

# ── TELEGRAM ─────────────────────────────────────
print("\n💬 TELEGRAM")
ts, tg = get_last("tg_activity")
if tg:
    try:
        data = json.loads(tg)
        print(f"   Сообщений за 7 дней : {data.get('messages_total', 0)}")
        print(f"   Активных чатов      : {data.get('active_chats', 0)}")
        if ts:
            t = datetime.datetime.strptime(ts[:19], '%Y-%m-%d %H:%M:%S')
            print(f"   Собрано             : {t.strftime('%m-%d %H:%M')}")
    except:
        pass

ts, tone = get_last("tg_tone")
if tone:
    try:
        data = json.loads(tone)
        total = sum(data.values())
        if total > 0:
            pos = data.get('positive', 0)
            neg = data.get('negative', 0)
            neu = data.get('neutral', 0)
            print(f"   Тональность         : 😊{pos} 😐{neu} 😟{neg}")
            dominant = max(data, key=data.get)
            emoji = "😊" if dominant=="positive" else "😟" if dominant=="negative" else "😐"
            print(f"   Преобладает         : {emoji} {dominant}")
    except:
        pass

ts, topics = get_last("tg_topics")
if topics:
    try:
        data = json.loads(topics)
        sorted_topics = sorted(data.items(), key=lambda x: x[1], reverse=True)[:3]
        print(f"   Топ темы            : {', '.join([f'{k}({v})' for k,v in sorted_topics])}")
    except:
        pass

# ── ЗАМЕТКИ СЕГОДНЯ ──────────────────────────────
print("\n📝 ЗАМЕТКИ")
notes = get_today("note")
if notes:
    print(f"   Сегодня : {len(notes)} заметок")
    for ts, v in notes[-3:]:
        t = datetime.datetime.strptime(ts[:19], '%Y-%m-%d %H:%M:%S')
        print(f"   {t.strftime('%H:%M')} — {v}")
else:
    print("   Сегодня заметок нет")
    print("   Добавить: note \"текст\"")

# ── СОН ──────────────────────────────────────────
print("\n😴 РЕЖИМ ДНЯ")
hour_counts = {}
all_batt = get_last_n("battery", 1440)
for ts, _ in all_batt:
    try:
        t = datetime.datetime.strptime(ts[:19], '%Y-%m-%d %H:%M:%S')
        h = t.hour
        hour_counts[h] = hour_counts.get(h, 0) + 1
    except:
        pass

if hour_counts:
    avg = sum(hour_counts.values()) / len(hour_counts)
    sleep_hours = sorted([h for h, c in hour_counts.items() if c < avg * 0.3])
    active_hours = sorted([h for h, c in hour_counts.items() if c >= avg * 0.7])
    if sleep_hours:
        print(f"   Вероятный сон    : {sleep_hours[0]:02d}:00 — {sleep_hours[-1]+1:02d}:00")
    if active_hours:
        print(f"   Активное время   : {active_hours[0]:02d}:00 — {active_hours[-1]+1:02d}:00")

# ── БАЗА ДАННЫХ ───────────────────────────────────
print("\n💾 БАЗА ДАННЫХ")
total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
size  = os.path.getsize("life_log_encrypted.db") / 1024
types = conn.execute(
    "SELECT COUNT(DISTINCT event_type) FROM events"
).fetchone()[0]
print(f"   Всего записей  : {total}")
print(f"   Типов данных   : {types}")
print(f"   Размер         : {size:.0f} КБ")

# Прогноз
first_ts = conn.execute("SELECT MIN(timestamp) FROM events").fetchone()[0]
if first_ts:
    try:
        t1 = datetime.datetime.strptime(first_ts[:19], '%Y-%m-%d %H:%M:%S')
        hours = max((now - t1).total_seconds() / 3600, 0.01)
        daily = size / hours * 24
        print(f"   Растёт          : ~{daily:.0f} КБ/день")
    except:
        pass

print("\n╔══════════════════════════════════════════════╗")
print("║  note \"текст\"  |  analyze  |  check         ║")
print("╚══════════════════════════════════════════════╝")

conn.close()
