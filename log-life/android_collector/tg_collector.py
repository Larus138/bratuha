import asyncio, sqlite3, datetime, os, json, re
from telethon import TelegramClient
from telethon.tl.types import User, Chat
from cryptography.fernet import Fernet
from collections import Counter

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

def get_last_scan():
    row = conn.execute(
        "SELECT value FROM events WHERE event_type='tg_last_scan' ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()
    if row:
        try:
            return datetime.datetime.fromisoformat(cipher.decrypt(row[0]).decode())
        except:
            pass
    return None

STOP_WORDS = {
    "и","в","на","с","по","к","за","из","от","до","не","что","как","это",
    "но","а","то","же","ты","я","он","она","мы","вы","они","да","нет",
    "так","уже","ещё","всё","там","тут","вот","есть","был","была","были",
    "быть","при","для","или","если","все","бы","мне","тебе","его","её",
    "об","во","со","без","под","над","между","через","после","перед",
    "только","тоже","даже","именно","очень","просто","можно","нужно",
    "надо","хочу","буду","будет","сейчас","когда","где","кто","чем","про"
}

POSITIVE = ["хорошо","отлично","спасибо","супер","круто","рад","успех","готово","класс","люблю"]
NEGATIVE = ["плохо","нет","проблема","устал","сложно","грустно","ошибка","не могу","тяжело"]
TOPICS   = {
    "work":    ["работа","проект","задача","бизнес","деньги","договор","братуха","клиент"],
    "tech":    ["код","python","скрипт","github","сервер","api","телеграм","программ"],
    "health":  ["здоровье","устал","сон","спать","еда","спорт","врач","болит"],
    "social":  ["встреча","друг","семья","кафе","погулять","созвониться","увидимся"],
    "emotion": ["чувствую","настроение","грустно","радостно","стресс","переживаю"],
    "finance": ["деньги","оплата","цена","стоимость","купить","продать","инвестиции"],
}

async def collect():
    client = TelegramClient('bratukha_session', API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        print("❌ Не авторизован. Запусти tg_auth.py")
        await client.disconnect()
        return

    last_scan = get_last_scan()
    if last_scan is None:
        since = datetime.datetime.now() - datetime.timedelta(days=365)
        label = "за год (первый запуск)"
    else:
        since = last_scan
        label = f"с {last_scan.strftime('%Y-%m-%d %H:%M')}"

    print(f"✅ Подключён к Telegram")
    print(f"🔄 Сбор данных {label}...")

    # Счётчики
    total_my      = 0
    total_their   = 0
    active_chats  = 0
    all_dialogs   = 0
    tone          = {"positive":0,"negative":0,"neutral":0}
    topics        = {}
    my_words      = Counter()
    their_words   = Counter()
    hour_stats    = {}
    day_stats     = {}

    async for dialog in client.iter_dialogs():
        try:
            all_dialogs += 1
            entity    = dialog.entity
            is_live   = False

            # Личный диалог
            if isinstance(entity, User) and not entity.bot:
                is_live = True
            # Малая группа до 7 человек
            elif isinstance(entity, Chat):
                if entity.participants_count and entity.participants_count <= 7:
                    is_live = True

            chat_msgs = 0

            async for msg in client.iter_messages(dialog.id, limit=500):
                if not msg.date: continue
                if msg.date.replace(tzinfo=None) < since: break
                if not msg.text: continue

                chat_msgs += 1
                text  = msg.text.lower()
                hour  = str(msg.date.hour)
                day   = msg.date.strftime('%Y-%m-%d')

                # Тональность и темы — для всех сообщений
                pos = sum(1 for w in POSITIVE if w in text)
                neg = sum(1 for w in NEGATIVE if w in text)
                if pos > neg: tone["positive"] += 1
                elif neg > pos: tone["negative"] += 1
                else: tone["neutral"] += 1

                for topic, kwords in TOPICS.items():
                    if any(w in text for w in kwords):
                        topics[topic] = topics.get(topic, 0) + 1
                        break
                else:
                    topics["other"] = topics.get("other", 0) + 1

                hour_stats[hour] = hour_stats.get(hour, 0) + 1
                day_stats[day]   = day_stats.get(day, 0) + 1

                # Слова — только из живых переписок
                if is_live:
                    words = re.findall(r'[а-яёa-z]{3,}', text)
                    words = [w for w in words if w not in STOP_WORDS]
                    if msg.out:
                        total_my += 1
                        my_words.update(words)
                    else:
                        total_their += 1
                        their_words.update(words)

            if chat_msgs > 0:
                active_chats += 1

        except Exception:
            continue

    # Сохраняем всё в базу
    save("tg_activity", {
        "period": label,
        "messages_my": total_my,
        "messages_their": total_their,
        "active_chats": active_chats,
        "all_dialogs": all_dialogs,
    })
    save("tg_tone",        tone)
    save("tg_topics",      topics)
    save("tg_hours",       hour_stats)
    save("tg_days",        day_stats)
    save("tg_words_my",    dict(my_words.most_common(50)))
    save("tg_words_their", dict(their_words.most_common(50)))
    save("tg_last_scan",   datetime.datetime.now().isoformat())

    print(f"✅ Готово:")
    print(f"   Диалогов всего   : {all_dialogs}")
    print(f"   Активных чатов   : {active_chats}")
    print(f"   Твоих сообщений  : {total_my}")
    print(f"   От собеседников  : {total_their}")
    if total_my + total_their > 0:
        ratio = total_my / (total_my + total_their) * 100
        print(f"   Ты пишешь        : {ratio:.0f}%")
    print(f"   Тональность      : {tone}")
    print(f"   Топ темы         : {dict(sorted(topics.items(), key=lambda x: x[1], reverse=True)[:5])}")
    print(f"✅ Все данные сохранены в зашифрованную базу")

    await client.disconnect()

asyncio.run(collect())
