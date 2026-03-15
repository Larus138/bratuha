import asyncio
from telethon import TelegramClient

API_ID   = 39533226
API_HASH = "2d72c95948b0ea145aa6c7ecc4ae92a5"

async def test():
    client = TelegramClient('bratukha_session', API_ID, API_HASH)
    await client.connect()

    count = 0
    async for dialog in client.iter_dialogs():
        count += 1
        if count <= 5:
            print(f"  Диалог: {dialog.name} | непрочитанных: {dialog.unread_count}")

    print(f"\nВсего диалогов: {count}")
    await client.disconnect()

asyncio.run(test())
