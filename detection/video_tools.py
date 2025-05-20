import cv2
import base64
import numpy as np

# Кодирование и декодирование кадра
def decode_base64_frame(data_url):
    try:
        header, encoded = data_url.split(",", 1)
        binary_data = base64.b64decode(encoded)
        np_arr = np.frombuffer(binary_data, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        return frame
    except Exception as e:
        print("Ошибка декодирования кадра:", e)
        return None


def encode_frame_to_base64(frame):
    if not isinstance(frame, np.ndarray):
        raise ValueError("encode_frame_to_base64: frame должен быть np.ndarray")
    _, buffer = cv2.imencode(".jpg", frame)
    encoded = base64.b64encode(buffer).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded}"
