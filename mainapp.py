import os
import threading
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, render_template, make_response, redirect, request, flash, url_for
from config.config import Config
from detection import socketio
from database import init_db, get_connection
from clients.report_routes import route_bp
from clients.auth import auth_bp
from clients.transmit_routes import transmit_bp
from clients.transmit_routes import api_bp
from clients.profile_routes import profile_bp
from flask_jwt_extended import JWTManager, verify_jwt_in_request, get_jwt_identity
from notifications import poll_updates
from protect import protected_route
from flasgger import Swagger, swag_from
from config.config_mail import mail

load_dotenv()
app = Flask(__name__)
app.config.from_object(Config)
mail.init_app(app)
jwt = JWTManager(app)
swagger = Swagger(app)

app.register_blueprint(auth_bp)
app.register_blueprint(transmit_bp)
app.register_blueprint(api_bp, url_prefix="/api")
app.register_blueprint(route_bp)
app.register_blueprint(profile_bp, url_prefix="/api")


# Страница трансляции
@app.route("/transmit", methods=["GET"])
@swag_from({
    "tags": ["Трансляция"],
    "summary": "Запуск трансляции камеры",
    "consumes": ["application/x-www-form-urlencoded"],
    "produces": ["text/html"],
    "parameters": [
        {
            "name": "camera_id",
            "in": "query",
            "type": "integer",
            "required": True,
            "description": "ID выбранной камеры"
        }
    ],
    "responses": {
        200: {"description": "Трансляция запущена"},
        400: {"description": "Камера не указана"},
        404: {"description": "Камера не найдена или не принадлежит пользователю"},
        401: {"description": "Отказ в доступе без авторизации"}
    }
})
@protected_route
def transmit():
    verify_jwt_in_request(locations=["cookies"])
    user_id = get_jwt_identity()

    camera_id = request.args.get("camera_id", type=int)

    if not user_id:
        return redirect("/login")

    if not camera_id:
        return "Не указана камера", 400

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT device_id FROM cameras WHERE id = %s AND user_id = %s", (camera_id, user_id))
    result = cur.fetchone()
    print(f"Камера: {result}")
    cur.close()
    conn.close()

    if not result:
        return "Камера не найдена или не ваша", 404

    device_id = result[0]

    return render_template("transmit.html", camera_id=camera_id, device_id=device_id)


# Страница просмотра
@app.route("/recieve", methods=["GET"])
@swag_from({
    "tags": ["Просмотр"],
    "summary": "Просмотр трансляции",
    "consumes": ["application/x-www-form-urlencoded"],
    "produces": ["text/html"],
    "responses": {
        200: {"description": "Трансляция отображена"},
        400: {"description": "Камера не указана"},
        401: {"description": "Неавторизованный пользователь"},
        404: {"description": "Камера не найдена или не существует"}
    }
})
@protected_route
def recieve():
    verify_jwt_in_request(locations=["cookies"])
    user_id = get_jwt_identity()
    camera_id = request.args.get("camera_id", type=int)

    if not user_id:
        return redirect("/login")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM cameras WHERE user_id = %s", (user_id,))
    cameras = cur.fetchall()

    camera_ids = [cam[0] for cam in cameras]

    if not camera_id or camera_id not in camera_ids:
        flash("Камера недоступна")
        return redirect(url_for("recieve_mode"))

    return render_template("recieve.html", camera_id=camera_id, cameras=cameras)


@app.route("/select")
@protected_route
def mode_select():
    return render_template("select.html")


@app.route("/logout")
def logout():
    response = make_response(redirect("/login"))
    response.delete_cookie("access_token")
    return response


@app.route("/")
def index():
    return redirect("/select")


if __name__ == "__main__":
    app.debug = True
    init_db()
    socketio.init_app(app)

    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Thread(target=poll_updates, daemon=True).start()

    socketio.run(app, host="0.0.0.0", port=5050, debug=True, allow_unsafe_werkzeug=True)
