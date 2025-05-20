import random

from flasgger import swag_from
from flask import Blueprint, render_template, request, redirect, session
from flask_jwt_extended import create_access_token, set_access_cookies
from passlib.hash import bcrypt
from database import get_connection
from flask_mail import Message
from config.config_mail import mail

auth_bp = Blueprint("auth", __name__)

# Для страницы регистрации и логина (в том числе подтверждения почты)


@swag_from({
    "tags": ["Вход"],
    "summary": "Вход в веб-приложение",
    "description": "Аутентификация пользователя по логину и паролю",
    "consumes": ["application/x-www-form-urlencoded"],
    "produces": ["text/html"],
    "parameters": [
        {
            "name": "username",
            "in": "formData",
            "type": "string",
            "required": True,
            "description": "Логин пользователя"
        },
        {
            "name": "password",
            "in": "formData",
            "type": "string",
            "required": True,
            "description": "Пароль пользователя"
        }
    ],
    "responses": {
        200: {"description": "Отображение страницы входа или вывод об ошибке ввода данных"},
        304: {"description": "Перенаправление на защищенную страницу"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
})
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, password_hash, email_verified
            FROM users
            WHERE username = %s
        """, (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and bcrypt.verify(password, user[1]):
            if not user[2]:
                return render_template("login.html", token="Email не подтверждён. Проверьте почту.")
            access_token = create_access_token(identity=str(user[0]))
            session["username"] = username
            resp = redirect("/select")
            set_access_cookies(resp, access_token)
            return resp
        else:
            return render_template("login.html", token="Неверный логин или пароль")

    return render_template("login.html")


@swag_from({
    "tags": ["Аутентификация"],
    "summary": "Регистрация нового пользователя",
    "description": "Создание нового пользователя по имени, email, логину и паролю.",
    "consumes": ["application/x-www-form-urlencoded"],
    "produces": ["text/html"],
    "parameters": [
        {
            "name": "name",
            "in": "formData",
            "type": "string",
            "required": True,
            "description": "Имя пользователя"
        },
        {
            "name": "email",
            "in": "formData",
            "type": "string",
            "required": True,
            "description": "Email пользователя"
        },
        {
            "name": "username",
            "in": "formData",
            "type": "string",
            "required": True,
            "description": "Логин пользователя"
        },
        {
            "name": "password",
            "in": "formData",
            "type": "string",
            "required": True,
            "description": "Пароль пользователя"
        },
    ],
    "responses": {
        200: {"description": "Отображение страницы регистрации, модульного окна или вывод об ошибке ввода данных"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
})
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    message = None
    verify_message = None
    show_verification_modal = False

    if request.method == "POST":
        # Проверка на отправку пользователем запроса из модульного окна
        if request.form.get("verify_email") == "1":
            code_entered = request.form.get("code")
            email = session.get("pending_email")

            if not email:
                verify_message = "Сессия устарела. Зарегистрируйтесь заново."
            # Проверка соответствие кода, введенного пользователем коду из таблицы бд
            else:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("""
                    SELECT u.id, ev.code FROM users u
                    JOIN email_verification_codes ev ON u.id = ev.user_id
                    WHERE u.email = %s
                """, (email,))
                row = cur.fetchone()
                # Удаление кода из таблицы в случае успешного подтверждения почты
                if row and row[1] == code_entered:
                    cur.execute("UPDATE users SET email_verified = true WHERE id = %s", (row[0],))
                    cur.execute("DELETE FROM email_verification_codes WHERE user_id = %s", (row[0],))
                    conn.commit()
                    verify_message = "Email подтверждён!"
                else:
                    verify_message = "Неверный код. Попробуйте снова."
                cur.close()
                conn.close()

            show_verification_modal = True
        # Запрос на регистрацию отправлен из основной страницы
        else:
            name = request.form.get("name")
            email = request.form.get("email")
            username = request.form.get("username")
            password = request.form.get("password")

            conn = get_connection()
            cur = conn.cursor()

            # Проверка на существование пользователя в бд по почте и логину
            cur.execute("SELECT id, email_verified FROM users WHERE email = %s", (email, ))
            user_exists_by_email = cur.fetchone()
            cur.execute("SELECT id, username FROM users WHERE username = %s", (username, ))
            user_exists_by_username = cur.fetchone()

            # Для исключения регистрации с уже имеющейся в таблице подтвержденной почтой
            if user_exists_by_email:
                if user_exists_by_email[1]:
                    message = "Пользователь с данной почтой уже существует"
                else:
                    # Для исключения регистрации, в которой логин существует с id,
                    # отличным от id неподтвержденной почты
                    if user_exists_by_username and user_exists_by_username[0] != user_exists_by_email[0]:
                        message = "Пользователь с данным логином уже существует"
                    # Если id логина и id почты одинаковы, значит пользователь ввел одинаковые данные,
                    # как при первой заброшенной попытке подтверждения почты
                    else:
                        code = ''.join(random.choices("0123456789", k=6))
                        password_hash = bcrypt.hash(password)

                        cur.execute("""
                            UPDATE users
                            SET username = %s, name = %s, password_hash = %s
                            WHERE id = %s
                        """, (username, name, password_hash, user_exists_by_email[0]))

                        cur.execute("DELETE FROM email_verification_codes WHERE user_id = %s",
                                    (user_exists_by_email[0],))

                        cur.execute("""
                            INSERT INTO email_verification_codes (user_id, code)
                            VALUES (%s, %s)
                        """, (user_exists_by_email[0], code))

                        conn.commit()

                        send_verification_code(email, code)
                        session["pending_email"] = email
                        message = "Email не был подтверждён. Данные обновлены, код выслан повторно."
                        show_verification_modal = True
            # Для исключения регистрации, в которой логин уже существует, а почта еще нет
            elif user_exists_by_username:
                message = "Пользователь с данным логином уже существует"
            else:
                code = ''.join(random.choices("0123456789", k=6))
                password_hash = bcrypt.hash(password)

                cur.execute("""
                                    INSERT INTO users (username, password_hash, name, email, email_verified)
                                    VALUES (%s, %s, %s, %s, false)
                                    RETURNING id
                                """, (username, password_hash, name, email))
                user_id = cur.fetchone()[0]

                cur.execute("""
                                    INSERT INTO email_verification_codes (user_id, code)
                                    VALUES (%s, %s)
                                """, (user_id, code))
                conn.commit()

                send_verification_code(email, code)
                session["pending_email"] = email
                message = "Регистрация прошла успешно! Подтвердите email."
                show_verification_modal = True

            cur.close()
            conn.close()

        return render_template("register.html",
                               message=message,
                               verify_message=verify_message,
                               show_verification_modal=show_verification_modal)


# Отправка на кода почту
def send_verification_code(user_email, verification_code):
    message = Message(
        subject="Подтверждение регистрации",
        recipients=[user_email],
        body=f"Ваш код подтверждения: {verification_code}. Введите его в строку."
    )
    mail.send(message)
