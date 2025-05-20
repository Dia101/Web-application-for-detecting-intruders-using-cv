from flasgger import swag_from
from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request, get_jwt
import random
import string
from database import get_connection
from protect import protected_route

profile_bp = Blueprint("profile", __name__)

# api для страницы (модульного окна) профиля


# Получение аккаунтов телеграмм
@profile_bp.route("/get_telegram_chats")
@protected_route
@swag_from({
    "tags": ["Окно профиля"],
    "summary": "Получить список привязанных тг-аккаунтов",
    "security": [{"cookieAuth": []}],
    "responses": {
        200: {
            "description": "Массив Телеграм-аккаунтов",
            "schema": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer", "example": 1},
                        "telegram_chat_id": {"type": "integer", "example": 123456789},
                        "telegram_username": {"type": "string",  "example": "myusername"}
                    }
                }
            }
        },
        401: {"description": "Истек срок действия токена или пользователь не авторизован"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
})
def get_telegram_chats():
    verify_jwt_in_request(locations=["cookies"])
    user_id = get_jwt_identity()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
            SELECT id, telegram_chat_id, telegram_username
            FROM telegram_chats
            WHERE user_id = %s
        """, (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    # формируем JSON для фронтенда
    return jsonify([
        {"id": row[0], "telegram_chat_id": row[1], "telegram_username": row[2]}
        for row in rows
    ])


# Генерация кода телеграм
@profile_bp.route("/generate_telegram_code", methods=["POST"])
@protected_route
@swag_from({
    "tags": ["Окно профиля"],
    "summary": "Генерация кода для привязки тг-аккаунта",
    "security": [{"cookieAuth": []}],
    "responses": {
        200: {
            "description": "Создание кода для привязки тг-аккаунта",
            "schema": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "example": "12345678"}
                }
            }
        },
        401: {"description": "Истек срок действия токена или пользователь не авторизован"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
})
def generate_telegram_code():
    verify_jwt_in_request(locations=["cookies"])

    jwt_data = get_jwt()

    user_id = jwt_data["sub"]
    code = ''.join(random.choices(string.digits, k=8))

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO telegram_codes (code, user_id) VALUES (%s, %s)", (code, user_id))
    conn.commit()
    cur.close()
    conn.close()
    print(code)
    return jsonify({"code": code})


# Удаление аккаунта
@profile_bp.route("/delete_telegram_chat/<int:id>", methods=["DELETE"])
@protected_route
@swag_from({
    "tags": ["Окно профиля"],
    "summary": "Удаление тг-канала из списка",
    "security": [{"cookieAuth": []}],
    "parameters": [
        {
            "name": "id",
            "in": "path",
            "type": "integer",
            "required": True,
            "description": "ID записи в таблице telegram_chats"
        }
    ],
    "responses": {
        204: {"description": "Успешное удаление, пустое тело ответа"},
        401: {"description": "Истек срок действия токена или пользователь не авторизован"},
        404: {"description": "Чат не найден или не принадлежит пользователю"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
})
def delete_telegram_chat(id):
    verify_jwt_in_request(locations=["cookies"])
    user_id = get_jwt_identity()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
            DELETE FROM telegram_chats
            WHERE id = %s AND user_id = %s
        """, (id, user_id))
    conn.commit()
    cur.close()
    conn.close()

    return "", 204


# Получение имени
@profile_bp.route("/get_user_name", methods=["GET"])
@protected_route
@swag_from({
    "tags": ["Окно профиля"],
    "summary": "Получить имя текущего пользователя",
    "security": [{"cookieAuth": []}],
    "responses": {
        200: {
            "description": "Создание кода для привязки тг-аккаунта",
            "schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "example": "Диана"}
                }
            }
        },
        401: {"description": "Истек срок действия токена или пользователь не авторизован"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
})
def get_user_name():
    verify_jwt_in_request(locations=["cookies"])
    user_id = get_jwt_identity()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    return jsonify({"name": row[0] if row else ""})
