import sqlite3, datetime, time, os, subprocess, json
from cryptography.fernet import Fernet

key_file = "secret.key"
if not os.path.exists(key_file):
    key = Fernet.generate_key()
    with open(key_file, "wb") as f: f.write(key)
else:
    with open(key_file, "rb") as f: key = f.read()

cipher = Fernet(key)
conn = sqlite3.connect("life_log_encrypted.db")
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS events (timestamp TEXT, event_type TEXT, value BLOB)")
conn.commit()

def get_battery():
    try:
        r = subprocess.run(['termux-battery-status'], capture_output=True, text=True, timeout=5)
        d = json.loads(r.stdout)
        return f"{d.get('percentage','?')}% | {d.get('status','?')} | {d.get('plugged','?')} | temp:{d.get('temperature','?')}C | current:{d.get('current','?')}uA"
    except:
        return "error"

def get_cpu_load():
    try:
        r = subprocess.run(['uptime'], capture_output=True, text=True, timeout=5)
        if 'load average' in r.stdout:
            return "load:" + r.stdout.split('load average:')[1].strip()
        return "unavailable"
    except:
        return "error"

def get_ram():
    try:
        info = {}
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                parts = line.split()
                if parts[0] in ('MemTotal:', 'MemAvailable:'):
                    info[parts[0]] = int(parts[1])
        total = info.get('MemTotal:', 0) // 1024
        avail = info.get('MemAvailable:', 0) // 1024
        used = total - avail
        pct = round(used / total * 100) if total > 0 else 0
        return f"used:{used}MB free:{avail}MB total:{total}MB ({pct}%)"
    except:
        return "error"

def get_disk():
    try:
        r = subprocess.run(['df', '-h', '/data/data/com.termux'], capture_output=True, text=True, timeout=5)
        lines = r.stdout.strip().split('\n')
        if len(lines) > 1:
            parts = lines[1].split()
            return f"size:{parts[1]} used:{parts[2]} free:{parts[3]} ({parts[4]})"
        return "error"
    except:
        return "error"

def get_internet():
    try:
        r = subprocess.run(['ping', '-c', '1', '-W', '3', '8.8.8.8'], capture_output=True, text=True, timeout=6)
        if r.returncode == 0:
            for line in r.stdout.split('\n'):
                if 'time=' in line:
                    return "online | ping:" + line.split('time=')[1].split()[0] + "ms"
            return "online"
        return "offline"
    except:
        return "error"

def get_uptime():
    try:
        r = subprocess.run(['uptime'], capture_output=True, text=True, timeout=5)
        if 'up' in r.stdout:
            return r.stdout.split('up')[1].split(',')[0].strip()
        return "unavailable"
    except:
        return "error"

def get_db_stats():
    try:
        c2 = conn.execute("SELECT COUNT(*) FROM events")
        total = c2.fetchone()[0]
        c3 = conn.execute("SELECT COUNT(*) FROM events WHERE timestamp >= datetime('now', '-1 hour', 'localtime')")
        last_hour = c3.fetchone()[0]
        return f"total:{total} last_hour:{last_hour}"
    except:
        return "error"

def get_weather():
    try:
        r = subprocess.run(['curl', '-s', '--max-time', '8', 'wttr.in/Irkutsk?format=%t+%C+%h+%w'], capture_output=True, text=True, timeout=10)
        result = r.stdout.strip()
        return result if result and len(result) < 100 else "unavailable"
    except:
        return "error"

cycle = 0
while True:
    now = datetime.datetime.now()
    cycle += 1
    events = {
        "battery":  get_battery(),
        "cpu_load": get_cpu_load(),
        "ram":      get_ram(),
        "disk":     get_disk(),
        "internet": get_internet(),
        "uptime":   get_uptime(),
        "db_stats": get_db_stats(),
    }
    if cycle % 30 == 1:
        events["weather"] = get_weather()
    for etype, val in events.items():
        encrypted_val = cipher.encrypt(str(val).encode())
        c.execute("INSERT INTO events VALUES (?, ?, ?)", (str(now), etype, encrypted_val))
    conn.commit()
    time.sleep(60)
