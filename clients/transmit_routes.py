from flasgger import swag_from
from flask import Blueprint, render_template, request, jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from protect import protected_route
from database import get_connection
from detection.socket_handlers import last_seen
import time

transmit_bp = Blueprint("transmit", __name__)
api_bp = Blueprint("api", __name__)


# Трансляция и просмотр


# Отображение списка камер на странице трансляции
@transmit_bp.route("/transmit_mode", methods=["GET"])
@protected_route
@swag_from({
    "tags": ["Камеры"],
    "summary": "Отображение списка камер",
    "consumes": ["application/x-www-form-urlencoded"],
    "produces": ["text/html"],
    "responses": {
        200: {"description": "Страница отображена успешно"},
        401: {"description": "Истек срок действия токена или пользователь не авторизован"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
})
def transmit_mode():
    verify_jwt_in_request(locations=["cookies"])
    user_id = get_jwt_identity()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM cameras WHERE user_id = %s", (user_id,))
    cameras = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("transmit_mode.html", cameras=cameras)


# Получение статуса реагирования на яркость
@api_bp.route("/cover_detection", methods=["GET"])
@protected_route
@swag_from({
    "tags": ["Камеры"],
    "summary": "Получить статус реагирования на яркость",
    "security": [{"cookieAuth": []}],
    "responses": {
        200: {
            "description": "Успешное получнеие статуса",
            "schema": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean", "example": True}
                }
            }
        },
        401: {"description": "Истек срок действия токена или пользователь не авторизован"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
})
def get_cover_detection():
    user_id = get_jwt_identity()
    cur = get_connection().cursor()
    cur.execute("SELECT detect_cover_enabled FROM users WHERE id = %s", (user_id,))
    enabled = bool(cur.fetchone()[0])
    cur.close()
    return jsonify(enabled=enabled), 200


# Обновление статуса реагирования на яркость
@api_bp.route("/cover_detection", methods=["POST"])
@protected_route
@swag_from({
    "tags": ["Камеры"],
    "summary": "Изменение статуса реагирования на яркость",
    "security": [{"cookieAuth": []}],
    "parameters": [
        {
            "name": "body",
            "in": "body",
            "required": True,
            "schema": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean"}
                },
                "required": ["enabled"]
            }
        }
    ],
    "responses": {
        200: {
            "description": "Успешное обновление статуса",
            "schema": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean", "example": True}
                }
            }
        },
        401: {"description": "Истек срок действия токена или пользователь не авторизован"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
})
def set_cover_detection():
    user_id = get_jwt_identity()
    enabled = bool(request.json.get("enabled", False))

    cur = get_connection().cursor()
    cur.execute(
        "UPDATE users SET detect_cover_enabled = %s WHERE id = %s",
        (enabled, user_id)
    )
    cur.connection.commit()
    cur.close()
    return jsonify(msg="updated", enabled=enabled), 200


# Добавление новой камеры
@swag_from({
    "tags": ["Камеры"],
    "summary": "Добавление новой камеры пользователю",
    "parameters": [
        {
            "name": "body",
            "in": "body",
            "required": True,
            "schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "device_id": {"type": "string"}
                },
                "required": ["name", "device_id"]
            }
        }
    ],
    "responses": {
        200: {"description": "Камера добавлена"},
        400: {"description": "Данные неполные или отсутствуют"},
        401: {"description": "Истек срок действия токена или пользователь не авторизован"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
})
@api_bp.route("/add_camera", methods=["POST"])
@protected_route
def add_camera():
    verify_jwt_in_request(locations=["cookies"])
    user_id = get_jwt_identity()
    data = request.get_json()

    if not data:
        return jsonify({"msg": "Отсутствуют данные запроса"}), 400

    name = data.get("name")
    device_id = data.get("device_id")

    if not name or not device_id:
        return jsonify({"msg": "Данные неполные"}), 400

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO cameras (name, user_id, device_id) VALUES (%s, %s, %s)", (name, user_id, device_id))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"msg": "Камера добавлена"}), 200


# Удаение камеры
@api_bp.route("/delete_camera/<int:camera_id>", methods=["DELETE"])
@protected_route
@swag_from({
    "tags": ["Камеры"],
    "summary": "Удаление камеры пользователя",
    "security": [{"cookieAuth": []}],
    "parameters": [
        {
            "name": "camera_id",
            "in": "path",
            "type": "integer",
            "required": True,
            "description": "ID камеры"
        }
    ],
    "responses": {
        204: {"description": "Камера успешно удалена"},
        401: {"description": "Истек срок действия токена или пользователь не авторизован"},
        404: {"description": "Камера не найдена"},
        500: {"description": "Ошибка сервера"}
    }
})
def delete_camera(camera_id):
    verify_jwt_in_request(locations=["cookies"])
    user_id = get_jwt_identity()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM cameras WHERE id = %s AND user_id = %s",
                (camera_id, user_id))
    conn.commit()
    cur.close()
    conn.close()
    return "", 204


# Просмотр видеопотока
@transmit_bp.route("/recieve_mode", methods=["GET"])
@swag_from({
    "tags": ["Камеры"],
    "summary": "Страница режима просмотра",
    "consumes": ["application/x-www-form-urlencoded"],
    "produces": ["text/html"],
    "responses": {
        200: {"description": "Страница успешно загружена"},
        401: {"description": "Истек срок действия токена или пользователь не авторизован"},
        500: {"description": "Ошибка сервера"}
    }
})
@protected_route
def recieve_mode():
    verify_jwt_in_request(locations=["cookies"])
    user_id = get_jwt_identity()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM cameras WHERE user_id = %s", (user_id,))
    cameras = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("recieve_mode.html", cameras=cameras)

# Проверка активности камеры
@api_bp.route("/is_camera_active")
def is_camera_active():
    print("Функция актива камеры")
    camera_id = request.args.get("camera_id", type=int)
    now = time.time()
    ts = last_seen.get(camera_id, 0)
    is_active = (now - ts) < 15
    return jsonify({"active": is_active})
