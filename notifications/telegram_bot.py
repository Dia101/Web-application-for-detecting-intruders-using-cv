import os
import requests
from database import get_connection
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')


# Отправка уведомления об угрозе
def send_alert(user_id: int, message: str, image_path: str = None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT telegram_chat_id FROM telegram_chats WHERE user_id = %s", (user_id,))
    chats_id = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()

    for chat_id in chats_id:
        try:
            if image_path:
                photo_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
                with open(image_path, "rb") as photo:
                    files = {"photo": photo}
                    caption = f"{message}"
                    data = {"chat_id": chat_id, "caption": caption}
                    requests.post(photo_url, data=data, files=files)
            print(f"Уведомление отправлено → {chat_id}")

        except Exception as e:
            print(f"Ошибка отправки Telegram ({chat_id}): {e}")
