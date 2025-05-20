import os
import requests
from database import get_connection
import time
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
LAST_UPDATE_ID = None
waiting_for_code = {}


# Отправка сообщений конкретному chat_id
def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    requests.post(url, data=data)


# Обработчик сообщений, проверка соответствия кода
def process_message(message):
    text = message.get("text", "").strip()
    chat_id = message["chat"]["id"]
    username = message["from"].get("username", "без имени")

    if text == "/start":
        waiting_for_code[chat_id] = True
        send_message(chat_id, "Введите 8-значный код для привязки:")
        return

    if chat_id not in waiting_for_code:
        send_message(chat_id, "Напишите /start, если хотите привязать данный аккаунт.")
        return

    if not text.isdigit() or len(text) != 8:
        send_message(chat_id, "Ошибка, Введите выданный 8-значный код.")
        return

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM telegram_codes WHERE code = %s", (text,))
    row = cur.fetchone()

    if row:
        user_id = row[0]
        cur.execute("""
            INSERT INTO telegram_chats (user_id, telegram_chat_id, telegram_username)
            VALUES (%s, %s, %s)
            ON CONFLICT (telegram_chat_id) DO NOTHING
        """, (user_id, chat_id, username))
        cur.execute("DELETE FROM telegram_codes WHERE code = %s", (text,))
        conn.commit()
        send_message(chat_id, "Успешная привязка аккаунта")
    else:
        send_message(chat_id, "Код не найден или уже использован")

    cur.close()
    conn.close()
    waiting_for_code.pop(chat_id, None)


# Прослушивание сообщений  запуск обработчика
def poll_updates():
    global LAST_UPDATE_ID

    while True:
        params = {"timeout": 10, "offset": LAST_UPDATE_ID}
        resp = requests.get(f"{BASE_URL}/getUpdates", params=params).json()

        for result in resp.get("result", []):
            LAST_UPDATE_ID = result["update_id"] + 1
            print(f"[{result['update_id']}] → {result}")
            if "message" in result:
                process_message(result["message"])

        time.sleep(2)


# Отправка текстовых сообщений всем привязанным аккаунтам (Для сниженной яркости)
def send_alert_to_user(user_id, text):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT telegram_chat_id FROM telegram_chats WHERE user_id = %s", (user_id,))
    chat_ids = cur.fetchall()
    cur.close()
    conn.close()

    for row in chat_ids:
        chat_id = row[0]
        send_message(chat_id, text)
