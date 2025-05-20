import os
import cv2
from datetime import datetime, timedelta
from notifications import send_alert
import threading
from database import get_connection

STATIC_REPORT_DIR = os.path.join("static", "reports")
os.makedirs(STATIC_REPORT_DIR, exist_ok=True)

MIN_INTERVAL = 60
last_saved_time = None


def create_event_report(event_data):
    global last_saved_time

    now = datetime.now()
    frame = event_data.get("frame")
    camera_id = int(event_data.get("camera_id", 0))
    user_id = int(event_data.get("user_id", 0))
    person_count = event_data.get("person_count", 0)

    if last_saved_time is None or (now - last_saved_time) > timedelta(seconds=MIN_INTERVAL):
        filename = f"detected_{now.strftime('%Y-%m-%d_%H-%M-%S')}_cam{camera_id}.jpg"
        screenshot_path = f"reports/{filename}"
        filepath = os.path.join(STATIC_REPORT_DIR, filename)

        cv2.imwrite(filepath, frame)
        last_saved_time = now

        print(f"Сохранение скриншота — Камера: {camera_id}, Людей: {person_count}, Время: {now.strftime('%H:%M:%S')}")

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM cameras WHERE id = %s", (camera_id,))
            row = cursor.fetchone()
            if row:
                camera_name = row[0]
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Не удалось получить имя камеры: {e}")

        message = (f"Обнаружена угроза!!!\n "
                   f"{person_count} человек(а)\n"
                   f"На объекте: {camera_name}!\n"
                   f"Время: {now.strftime('%Y-%m-%d %H:%M:%S')}")

        # Отправка уведомления в отдельном потоке
        threading.Thread(target=send_alert, args=(user_id, message, filepath)).start()

        # Сохранение события в базе данных в отдельном потоке
        threading.Thread(
            target=save_event_to_db,
            args=(camera_id, user_id, person_count, now, screenshot_path)
        ).start()

        return True
    else:
        return False


def save_event_to_db(camera_id, user_id, person_count, timestamp, screenshot_path):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO events (camera_id, user_id, person_count, timestamp, screenshot_path)
            VALUES (%s, %s, %s, %s, %s)
        """, (camera_id, user_id, person_count, timestamp, screenshot_path))
        conn.commit()
        cursor.close()
        conn.close()
        print("Событие сохранено в базе")
    except Exception as e:
        print(f"Ошибка при сохранении события в БД: {e}")
