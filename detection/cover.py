import time
import cv2
import numpy as np

from notifications import send_alert_to_user

dark_start_times = {}


# Функция реагирования на снижения яркости
def brightness_monitor(frame, camera_id, user_id, cover_detection):
    if not cover_detection.get(user_id, False):
        return
    brightness = np.mean(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))

    if brightness < 30:
        if user_id not in dark_start_times:
            dark_start_times[user_id] = time.time()
        elif time.time() - dark_start_times[user_id] > 10:
            # Отправка уведомления
            text = f"Обнаружено перекрытие камеры (ID {camera_id}) более 10 секунд"
            send_alert_to_user(user_id, text)
            dark_start_times[user_id] = time.time() + 600
    else:
        dark_start_times.pop(user_id, None)
