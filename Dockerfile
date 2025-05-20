FROM python:3.10-slim
LABEL authors="Diank"

RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# Указываем порт
EXPOSE 5050

# Запускаем приложение
CMD ["python", "mainapp.py"]
