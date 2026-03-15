import sqlite3, datetime, os
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

def get_all(event_type):
    rows = conn.execute(
        "SELECT timestamp, value FROM events WHERE event_type=? ORDER BY timestamp",
        (event_type,)
    ).fetchall()
    result = []
    for ts, val in rows:
        try:
            t = datetime.datetime.strptime(ts[:19], '%Y-%m-%d %H:%M:%S')
            v = decrypt(val)
            result.append((t, v))
        except:
            pass
    return result

def get_by_day(event_type):
    data = get_all(event_type)
    by_day = {}
    for t, v in data:
        day = t.date()
        if day not in by_day:
            by_day[day] = []
        by_day[day].append((t, v))
    return by_day

print("================================================")
print("   DIGITAL TWIN — АНАЛИЗ ПАТТЕРНОВ v2")
print(f"   {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("================================================")

print("\n[ 1 ] РЕЖИМ СНА И АКТИВНОСТИ")
battery_data = get_all("battery")
hour_counts = {}
for t, v in battery_data:
    h = t.hour
    hour_counts[h] = hour_counts.get(h, 0) + 1

if hour_counts:
    avg = sum(hour_counts.values()) / len(hour_counts)
    sleep_hours = sorted([h for h, cnt in hour_counts.items() if cnt < avg * 0.4])
    active_hours = sorted([h for h, cnt in hour_counts.items() if cnt >= avg * 0.7])
    if sleep_hours:
        print(f"  😴 Вероятный сон    : {sleep_hours[0]}:00 — {sleep_hours[-1]+1}:00")
    if active_hours:
        print(f"  📱 Активен          : {active_hours[0]}:00 — {active_hours[-1]+1}:00")
    most_active = max(hour_counts.items(), key=lambda x: x[1])
    least_active = min(hour_counts.items(), key=lambda x: x[1])
    print(f"  🔥 Пик активности   : {most_active[0]}:00 ({most_active[1]} записей)")
    print(f"  💤 Минимум          : {least_active[0]}:00 ({least_active[1]} записей)")

print("\n[ 2 ] ПРОДУКТИВНЫЕ ЧАСЫ (по CPU)")
cpu_data = get_all("cpu_load")
hour_load = {}
hour_count = {}
for t, v in cpu_data:
    try:
        load = float(v.split('load:')[1].split(',')[0].strip())
        h = t.hour
        hour_load[h] = hour_load.get(h, 0) + load
        hour_count[h] = hour_count.get(h, 0) + 1
    except:
        pass

if hour_load:
    hour_avg = {h: hour_load[h]/hour_count[h] for h in hour_load}
    sorted_hours = sorted(hour_avg.items(), key=lambda x: x[1], reverse=True)
    print(f"  🔥 Топ активных часов:")
    for h, load in sorted_hours[:5]:
        bar = "█" * min(int(load/2), 25)
        print(f"    {h:02d}:00  {bar} {load:.1f}")
    print(f"  💤 Тихие часы:")
    for h, load in sorted_hours[-3:]:
        bar = "░" * min(int(load/2), 25)
        print(f"    {h:02d}:00  {bar} {load:.1f}")

print("\n[ 3 ] ТРЕНДЫ ПО ДНЯМ")
battery_by_day = get_by_day("battery")
cpu_by_day = get_by_day("cpu_load")
ram_by_day = get_by_day("ram")
all_days = sorted(set(list(battery_by_day.keys()) + list(cpu_by_day.keys())))

for day in all_days:
    dow = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"][day.weekday()]
    print(f"\n  📅 {day.strftime('%Y-%m-%d')} {dow}")
    if day in battery_by_day:
        levels = []
        charges = 0
        prev_pct = None
        for t, v in battery_by_day[day]:
            try:
                pct = int(v.split('%')[0])
                levels.append(pct)
                if prev_pct is not None and pct > prev_pct + 15:
                    charges += 1
                prev_pct = pct
            except:
                pass
        if levels:
            print(f"    🔋 Батарея : {min(levels)}%→{max(levels)}% avg:{sum(levels)//len(levels)}% зарядок:{charges}")
    if day in cpu_by_day:
        loads = []
        for t, v in cpu_by_day[day]:
            try:
                load = float(v.split('load:')[1].split(',')[0].strip())
                loads.append(load)
            except:
                pass
        if loads:
            print(f"    ⚙️  CPU    : avg:{sum(loads)/len(loads):.1f} max:{max(loads):.1f} min:{min(loads):.1f}")
    if day in ram_by_day:
        used_list = []
        for t, v in ram_by_day[day]:
            try:
                used = int(v.split('used:')[1].split('MB')[0])
                used_list.append(used)
            except:
                pass
        if used_list:
            print(f"    🧠 RAM    : avg:{sum(used_list)//len(used_list)}MB max:{max(used_list)}MB")
    if day in battery_by_day:
        records = len(battery_by_day[day])
        print(f"    📊 Записей: {records} (~{records//60}ч активности)")

print("\n[ 4 ] АВТОМАТИЧЕСКИЕ ВЫВОДЫ")
if battery_data:
    levels = []
    low_count = 0
    charges = 0
    prev_pct = None
    for t, v in battery_data:
        try:
            pct = int(v.split('%')[0])
            levels.append(pct)
            if pct < 20:
                low_count += 1
            if prev_pct is not None and pct > prev_pct + 15:
                charges += 1
            prev_pct = pct
        except:
            pass
    if levels:
        avg = sum(levels) / len(levels)
        print(f"  🔋 Средний заряд : {avg:.0f}%")
        print(f"  🔌 Циклов зарядки: {charges}")
        if low_count > 5:
            print(f"  ⚠️  {low_count} раз заряд падал ниже 20%")
        if avg > 70:
            print(f"  ✅ Хорошо следишь за зарядкой")
        else:
            print(f"  ⚠️  Часто разряжаешь телефон")

if cpu_data:
    loads = []
    for t, v in cpu_data:
        try:
            load = float(v.split('load:')[1].split(',')[0].strip())
            loads.append(load)
        except:
            pass
    if loads:
        avg_load = sum(loads) / len(loads)
        if avg_load > 15:
            print(f"  ⚠️  Постоянно высокая нагрузка CPU ({avg_load:.1f})")
        else:
            print(f"  ✅ Нормальная нагрузка CPU ({avg_load:.1f})")

net_data = get_all("internet")
if net_data:
    offline = sum(1 for _, v in net_data if 'offline' in v)
    total_net = len(net_data)
    pct = (total_net - offline) / total_net * 100 if total_net > 0 else 0
    print(f"  🌐 Интернет стабильность: {pct:.0f}% (обрывов: {offline})")

notes = get_all("note")
if notes:
    print(f"  📝 Заметок сохранено: {len(notes)}")
    for t, v in notes:
        print(f"    {t.strftime('%m-%d %H:%M')} — {v}")
else:
    print(f"  💡 Заметок нет — используй: note \"текст\"")

print("\n[ 5 ] СТАТИСТИКА БАЗЫ")
total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
types = conn.execute(
    "SELECT event_type, COUNT(*) FROM events GROUP BY event_type ORDER BY COUNT(*) DESC"
).fetchall()
size = os.path.getsize("life_log_encrypted.db") / 1024
first_ts = conn.execute("SELECT MIN(timestamp) FROM events").fetchone()[0]
last_ts = conn.execute("SELECT MAX(timestamp) FROM events").fetchone()[0]

print(f"  📊 Всего записей : {total}")
print(f"  💾 Размер базы   : {size:.0f} КБ")
if first_ts and last_ts:
    t1 = datetime.datetime.strptime(first_ts[:19], '%Y-%m-%d %H:%M:%S')
    t2 = datetime.datetime.strptime(last_ts[:19], '%Y-%m-%d %H:%M:%S')
    hours = (t2 - t1).total_seconds() / 3600
    print(f"  ⏱️  Период         : {hours:.1f} часов")
    print(f"  📈 Записей/час    : {total/hours:.0f}")
print(f"  Типы данных:")
for etype, cnt in types:
    bar = "▪" * min(cnt // 10, 30)
    print(f"    {etype:<15} {cnt:>5}  {bar}")

print("\n================================================")
conn.close()
