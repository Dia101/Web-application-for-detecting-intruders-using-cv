from flask import request, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from flask_socketio import SocketIO, emit, join_room

from database import get_connection
from detection import detect_person
from detection.cover import brightness_monitor
from detection.video_tools import decode_base64_frame, encode_frame_to_base64
from reporting.reporter import create_event_report
import cv2
import threading
import time

socketio = SocketIO(cors_allowed_origins='*')
NMS_MAX_TIME = 0.55
last_brightness_check = 0
cover_detection = {}
active_cameras = set()
last_seen = {}

# Управление модулем детекции
@socketio.on('frame')
def handle_frame(data):
    global last_brightness_check
    try:
        base64_image = data.get("image")
        frame = decode_base64_frame(base64_image)
        camera_id = int(data.get("camera_id", 0))

        try:
            verify_jwt_in_request(locations=["cookies"])
            user_id = int(get_jwt_identity())
        except Exception as e:
            print(f"Ошибка получнеия user_id: {e}")
            user_id = 0

        if frame is None:
            print("Кадр не распознан")
            return

        if cover_detection.get(user_id, False):
            if time.time() - last_brightness_check > 10:
                last_brightness_check = time.time()
                threading.Thread(
                    target=brightness_monitor,
                    args=(frame, camera_id, user_id, cover_detection)
                ).start()

        start = time.perf_counter()
        people = detect_person(frame)
        duration = time.perf_counter() - start

        if duration > NMS_MAX_TIME:
            print(f"Долгая детекция ({duration:.3f}s), пропуск кадра")
            return

        # Рамки для людей
        for person in people:
            bbox = person["bbox"]
            cv2.rectangle(frame, (bbox["xmin"], bbox["ymin"]),
                          (bbox["xmax"], bbox["ymax"]), (0, 255, 0), 2)
            cv2.putText(frame, f"Person: {person['confidence']:.2f}",
                        (bbox["xmin"], bbox["ymin"] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        if people:
            event_data = {
                "frame": frame.copy(),
                "camera_id": camera_id,
                "user_id": user_id,
                "person_count": len(people)
            }
            threading.Thread(target=create_event_report, args=(event_data,)).start()

        # Кодируем обработанный кадр и отправляем
        encoded = encode_frame_to_base64(frame)
        emit("processed_frame", encoded, broadcast=True)
    except Exception as e:
        print(f"Ошибка обработки кадра: {e}")


# Переключение режима реагирования на яркость
@socketio.on("camera_settings")
def handle_camera_settings(data):
    try:
        verify_jwt_in_request(locations=["cookies"])
        user_id = int(get_jwt_identity())

        detect_cover = bool(data.get("detect_cover", False))
        cover_detection[user_id] = detect_cover

        # Сохраняем в базе данных
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET detect_cover_enabled = %s WHERE id = %s", (detect_cover, user_id))
        conn.commit()
        cur.close()
        conn.close()

        # Рассылка после обнаружения
        emit("update_cover_toggle", {"detect_cover": detect_cover}, to=f"user_{user_id}")
        print(f"[USER {user_id}] detect_cover = {detect_cover}")
    except Exception as e:
        print(f"Ошибка в camera_settings: {e}")


@socketio.on("camera_ping")
def handle_ping(data):
    global last_seen
    camera_id = data.get("camera_id")
    if camera_id:
        last_seen[int(camera_id)] = time.time()

