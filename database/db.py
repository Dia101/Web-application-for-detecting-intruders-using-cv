import psycopg2
import os
from dotenv import load_dotenv

# Инфициализация базы данных

load_dotenv()

DB_PARAMS = {
    "dbname": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
    "host": os.getenv("POSTGRES_HOST"),
    "port": os.getenv("POSTGRES_PORT")
}


def init_db():
    print("Инициализация базы данных...")
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        print("Подключено к базе:", conn.get_dsn_parameters()["dbname"])
        cursor = conn.cursor()

        # Таблица пользователей
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name VARCHAR(100),
            email VARCHAR(100),
            detect_cover_enabled BOOLEAN DEFAULT FALSE,
            email_verified BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)

        # Таблица камер
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS cameras (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            user_id INT REFERENCES users(id),
            device_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)

        # Таблица событий
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id SERIAL PRIMARY KEY,
            camera_id INT REFERENCES cameras(id),
            user_id INT REFERENCES users(id),
            person_count INT,
            timestamp TIMESTAMP,
            screenshot_path TEXT
        );
        """)

        # Телеграм-чаты
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS telegram_chats (
            id SERIAL PRIMARY KEY,
            user_id INT REFERENCES users(id) ON DELETE CASCADE,
            telegram_chat_id BIGINT UNIQUE,
            telegram_username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Телеграм-коды
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS telegram_codes (
            code CHAR(8) PRIMARY KEY,
            user_id INT REFERENCES users(id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Коды для почты
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS email_verification_codes (
                    id SERIAL PRIMARY KEY,
                    user_id INT REFERENCES users(id) ON DELETE CASCADE,
                    code VARCHAR(10) NOT NULL,
                    expiration_time TIMESTAMP NOT NULL
                );
                """)

        conn.commit()
        cursor.close()
        conn.close()

        print("Все таблицы успешно созданы")

    except Exception as e:
        print(f"Ошибка при инициализации базы данных: {e}")


def get_connection():
    return psycopg2.connect(**DB_PARAMS)
