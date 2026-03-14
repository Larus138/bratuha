#!/data/data/com.termux/files/usr/bin/python
import sqlite3
from cryptography.fernet import Fernet
import sys
from datetime import datetime

DB_PATH = "life_log_encrypted.db"
KEY_FILE = "secret.key"

def load_key():
    with open(KEY_FILE, "rb") as f:
        return f.read()

def decrypt_value(encrypted_blob, cipher):
    try:
        decrypted = cipher.decrypt(encrypted_blob)
        return decrypted.decode('utf-8')
    except Exception as e:
        return f"<decrypt error: {e}>"

def view_last(limit=10, show_all=False):
    key = load_key()
    cipher = Fernet(key)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Проверим, есть ли таблица events
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events'")
    if not c.fetchone():
        print("Таблица 'events' не найдена в базе.")
        return

    # Получаем записи
    query = "SELECT timestamp, event_type, value FROM events ORDER BY timestamp DESC"
    if not show_all:
        query += f" LIMIT {limit}"
    c.execute(query)
    rows = c.fetchall()

    if not rows:
        print("Нет записей в базе.")
        return

    print("\n===== DECRYPTED LOGS =====")
    for ts, etype, enc_val in rows:
        decrypted = decrypt_value(enc_val, cipher)
        # Попробуем распарсить timestamp для красоты, но можно просто вывести
        print(f"{ts} | {etype} | {decrypted}")

    conn.close()

def show_help():
    print("Использование: python view_logs.py [число] [--all]")
    print("  число   - количество последних записей (по умолчанию 10)")
    print("  --all   - показать все записи (без ограничения)")

if __name__ == "__main__":
    limit = 10
    show_all = False
    for arg in sys.argv[1:]:
        if arg == "--all":
            show_all = True
        elif arg.isdigit():
            limit = int(arg)
        else:
            print(f"Неизвестный аргумент: {arg}")
            show_help()
            sys.exit(1)

    view_last(limit, show_all)
