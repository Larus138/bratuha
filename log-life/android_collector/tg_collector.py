import asyncio, sqlite3, datetime, os, json
from telethon import TelegramClient
from cryptography.fernet import Fernet

os.chdir(os.path.dirname(os.path.abspath(__file__)))

API_ID   = 39533226
API_HASH = "2d72c95948b0ea145aa6c7ecc4ae92a5"

with open("secret.key", "rb") as f:
    key = f.read()
cipher = Fernet(key)

conn = sqlite3.connect("life_log_encrypted.db")
conn.execute("CREATE TABLE IF NOT EXISTS events (timestamp TEXT, event_type TEXT, value BLOB)")
conn.commit()

def save(event_type, data):
    now = str(datetime.datetime.now())
    encrypted = cipher.encrypt(json.dumps(data, ensure_ascii=False).encode())
    conn.execute("INSERT INTO events VALUES (?, ?, ?)", (now, event_type, encrypted))
    conn.commit()

def detect_tone(text):
    if not text: return "neutral"
    text = text.lower()
    pos = sum(1 for w in ["хорошо","отлично","спасибо","супер","круто","рад","успех","готово","да","класс"] if w in text)
    neg = sum(1 for w in ["плохо","нет","проблема","устал","сложно","грустно","ошибка","не могу"] if w in text)
    if pos > neg: return "positive"
    if neg > pos: return "negative"
    return "neutral"

def detect_topic(text):
    if not text: return "other"
    text = text.lower()
    topics = {
        "work":    ["работа","проект","задача","бизнес","деньги","договор","братуха"],
        "tech":    ["код","python","скрипт","github","сервер","api","телеграм"],
        "health":  ["здоровье","устал","сон","спать","еда","спорт"],
        "social":  ["встреча","друг","семья","кафе","погулять"],
        "emotion": ["чувствую","настроение","грустно","радостно","стресс"],
    }
    for topic, words in topics.items():
        if any(w in text for w in words):
            return topic
    return "other"

async def collect():
    client = TelegramClient('bratukha_session', API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        print("❌ Не авторизован. Запусти tg_auth.py")
        await client.disconnect()
        return

    print("✅ Подключён к Telegram")
    print("🔄 Сбор данных за последние 7 дней...")

    since = datetime.datetime.now() - datetime.timedelta(days=7)
    total = 0
    active_chats = 0
    tone_stats = {"positive":0,"negative":0,"neutral":0}
    topic_stats = {}
    hour_stats = {}
    day_stats = {}

    async for dialog in client.iter_dialogs():
        try:
            chat_msgs = 0
            async for msg in client.iter_messages(dialog.id, limit=200):
                if not msg.date:
                    continue
                msg_time = msg.date.replace(tzinfo=None)
                if msg_time < since:
                    break
                if not msg.text:
                    continue

                # Считаем все сообщения — входящие и исходящие
                chat_msgs += 1
                total += 1
                tone  = detect_tone(msg.text)
                topic = detect_topic(msg.text)
                hour  = str(msg.date.hour)
                day   = msg_time.strftime('%Y-%m-%d')

                tone_stats[tone]   = tone_stats.get(tone, 0) + 1
                topic_stats[topic] = topic_stats.get(topic, 0) + 1
                hour_stats[hour]   = hour_stats.get(hour, 0) + 1
                day_stats[day]     = day_stats.get(day, 0) + 1

            if chat_msgs > 0:
                active_chats += 1

        except Exception:
            continue

    save("tg_activity", {
        "period": "7d",
        "messages_total": total,
        "active_chats": active_chats,
    })
    save("tg_tone",   tone_stats)
    save("tg_topics", topic_stats)
    save("tg_hours",  hour_stats)
    save("tg_days",   day_stats)

    print(f"✅ Готово:")
    print(f"   Сообщений за 7 дней  : {total}")
    print(f"   Активных чатов       : {active_chats}")
    print(f"   Тональность          : {tone_stats}")
    print(f"   Темы                 : {topic_stats}")
    print(f"   По дням              : {day_stats}")
    print(f"✅ Оригинальные тексты НЕ сохранены")

    await client.disconnect()

asyncio.run(collect())
