import sqlite3, datetime, json, os
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

print("================================================")
print("   АНАЛИЗ ПАТТЕРНОВ — DIGITAL TWIN")
print(f"   {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("================================================")

# --- АНАЛИЗ СНА ---
print("\n[ СОН И АКТИВНОСТЬ ]")
battery_data = get_all("battery")
if battery_data:
    by_hour = {}
    for t, v in battery_data:
        h = t.hour
        if h not in by_hour:
            by_hour[h] = []
        by_hour[h].append(v)

    # Определяем активные и пассивные часы
    active_hours = []
    passive_hours = []
    for h in sorted(by_hour.keys()):
        count = len(by_hour[h])
        if count >= 50:
            active_hours.append(h)
        elif count <= 10:
            passive_hours.append(h)

    if active_hours:
        print(f"  📱 Активные часы    : {', '.join([f'{h}:00' for h in active_hours])}")
    if passive_hours:
        print(f"  😴 Пассивные часы   : {', '.join([f'{h}:00' for h in passive_hours])}")

# --- АНАЛИЗ БАТАРЕИ ---
print("\n[ БАТАРЕЯ ]")
if battery_data:
    levels = []
    for t, v in battery_data:
        try:
            pct = int(v.split('%')[0])
            levels.append((t, pct))
        except:
            pass

    if levels:
        # Минимум и максимум
        min_pct = min(levels, key=lambda x: x[1])
        max_pct = max(levels, key=lambda x: x[1])
        avg_pct = sum(x[1] for x in levels) / len(levels)

        print(f"  🔋 Средний заряд    : {avg_pct:.0f}%")
        print(f"  ⬇️  Минимум          : {min_pct[1]}% в {min_pct[0].strftime('%H:%M')}")
        print(f"  ⬆️  Максимум         : {max_pct[1]}% в {max_pct[0].strftime('%H:%M')}")

        # Циклы зарядки
        charges = 0
        prev = None
        for t, pct in levels:
            if prev is not None and pct > prev + 10:
                charges += 1
            prev = pct
        print(f"  🔌 Циклов зарядки   : {charges}")

        # Скорость разряда
        discharging = [(t, pct) for t, pct in levels if pct > 0]
        if len(discharging) > 10:
            first_t, first_pct = discharging[0]
            last_t, last_pct = discharging[-1]
            hours = max((last_t - first_t).total_seconds() / 3600, 0.01)
            drain = (first_pct - last_pct) / hours
            if drain > 0:
                print(f"  📉 Разряд           : {drain:.1f}%/час")
                remaining = last_pct / drain if drain > 0 else 0
                print(f"  ⏱️  До разряда       : {remaining:.1f} часов (при текущем темпе)")

# --- АНАЛИЗ CPU ---
print("\n[ НАГРУЗКА ПРОЦЕССОРА ]")
cpu_data = get_all("cpu_load")
if cpu_data:
    loads = []
    for t, v in cpu_data:
        try:
            load = float(v.split('load:')[1].split(',')[0].strip())
            loads.append((t, load))
        except:
            pass

    if loads:
        avg_load = sum(x[1] for x in loads) / len(loads)
        max_load = max(loads, key=lambda x: x[1])
        min_load = min(loads, key=lambda x: x[1])
        print(f"  ⚙️  Средняя нагрузка : {avg_load:.1f}")
        print(f"  🔥 Максимум         : {max_load[1]:.1f} в {max_load[0].strftime('%H:%M')}")
        print(f"  💤 Минимум          : {min_load[1]:.1f} в {min_load[0].strftime('%H:%M')}")

        if avg_load > 10:
            print(f"  ⚠️  Высокая нагрузка — телефон работает интенсивно")

# --- АНАЛИЗ RAM ---
print("\n[ ПАМЯТЬ ]")
ram_data = get_all("ram")
if ram_data:
    used_list = []
    for t, v in ram_data:
        try:
            used = int(v.split('used:')[1].split('MB')[0])
            used_list.append((t, used))
        except:
            pass

    if used_list:
        avg_used = sum(x[1] for x in used_list) / len(used_list)
        max_used = max(used_list, key=lambda x: x[1])
        min_used = min(used_list, key=lambda x: x[1])
        print(f"  🧠 Среднее использование : {avg_used:.0f} MB")
        print(f"  ⬆️  Максимум             : {max_used[1]} MB в {max_used[0].strftime('%H:%M')}")
        print(f"  ⬇️  Минимум              : {min_used[1]} MB в {min_used[0].strftime('%H:%M')}")

# --- ЗАМЕТКИ ---
print("\n[ ЗАМЕТКИ ]")
notes = get_all("note")
if notes:
    print(f"  📝 Всего заметок : {len(notes)}")
    print(f"  Последние:")
    for t, v in notes[-3:]:
        print(f"    {t.strftime('%m-%d %H:%M')} — {v}")
else:
    print("  Заметок пока нет")

# --- ИНТЕРНЕТ ---
print("\n[ ИНТЕРНЕТ ]")
net_data = get_all("internet")
if net_data:
    online = sum(1 for _, v in net_data if 'online' in v)
    offline = sum(1 for _, v in net_data if 'offline' in v)
    total = len(net_data)
    pct_online = online / total * 100 if total > 0 else 0
    print(f"  🌐 Онлайн : {online} раз ({pct_online:.0f}%)")
    print(f"  ❌ Офлайн : {offline} раз")

    pings = []
    for _, v in net_data:
        try:
            ping = float(v.split('ping:')[1].split('ms')[0])
            pings.append(ping)
        except:
            pass
    if pings:
        print(f"  📶 Средний пинг : {sum(pings)/len(pings):.1f}ms")

# --- ОБЩАЯ СТАТИСТИКА ---
print("\n[ ОБЩАЯ СТАТИСТИКА ]")
total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
first_ts = conn.execute("SELECT MIN(timestamp) FROM events").fetchone()[0]
last_ts  = conn.execute("SELECT MAX(timestamp) FROM events").fetchone()[0]

if first_ts and last_ts:
    fmt = '%Y-%m-%d %H:%M:%S.%f'
    try:
        t1 = datetime.datetime.strptime(first_ts, fmt)
        t2 = datetime.datetime.strptime(last_ts, fmt)
        hours = (t2 - t1).total_seconds() / 3600
        print(f"  📊 Всего записей  : {total}")
        print(f"  ⏱️  Период          : {hours:.1f} часов")
        print(f"  📅 С              : {t1.strftime('%Y-%m-%d %H:%M')}")
        print(f"  📅 По             : {t2.strftime('%Y-%m-%d %H:%M')}")
        rph = total / hours if hours > 0 else 0
        print(f"  📈 Записей/час    : {rph:.0f}")
    except:
        pass

print("\n================================================")
conn.close()
