import sqlite3, datetime, sys, os
from cryptography.fernet import Fernet

if len(sys.argv) < 2:
    print("Использование: python note.py \"твой текст\"")
    sys.exit(1)

text = " ".join(sys.argv[1:])
os.chdir(os.path.dirname(os.path.abspath(__file__)))

with open("secret.key", "rb") as f:
    key = f.read()

cipher = Fernet(key)
conn = sqlite3.connect("life_log_encrypted.db")
now = str(datetime.datetime.now())
encrypted = cipher.encrypt(text.encode())
conn.execute("INSERT INTO events VALUES (?, ?, ?)", (now, "note", encrypted))
conn.commit()
conn.close()
print(f"✅ Заметка сохранена: {now}")
