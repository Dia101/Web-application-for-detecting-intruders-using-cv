from flasgger import swag_from
from flask import Blueprint, render_template, request, jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from protect import protected_route
from database import get_connection

route_bp = Blueprint("route", __name__)

# Составление отчетов
@route_bp.route("/report", methods=["GET"])
@swag_from({
    "tags": ["Отчеты"],
    "summary": "Отчетность по событиям",
    "description": "Отображает таблицу событий: время, камера, количество людей, скриншот.",
    "consumes": ["application/x-www-form-urlencoded"],
    "produces": ["text/html"],
    "responses": {
        200: {"description": "Успешный доступ к отчетам"},
        401: {"description": "Требуется аутентификация"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
})
@protected_route
def report():
    verify_jwt_in_request(locations=["cookies"])
    user_id = get_jwt_identity()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT e.timestamp, c.name, e.person_count, e.screenshot_path
        FROM events e
        JOIN cameras c ON e.camera_id = c.id
        WHERE e.user_id = %s
        ORDER BY e.timestamp DESC
    """, (user_id,))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    events = [
        {
            "timestamp": row[0].strftime("%Y-%m-%d %H:%M:%S"),
            "camera_name": row[1],
            "person_count": row[2],
            "screenshot_path": row[3]
        }
        for row in rows
    ]

    return render_template("report.html", events=events)
