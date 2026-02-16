FROM python:3.11-slim

# Устанавливаем системные пакеты для компиляции
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    python3-dev \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libswresample-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем requirements и обновляем pip
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip

# Пытаемся установить зависимости. Если какая-то не соберётся, будет видно в логах
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальной код
COPY . .

# Команда запуска (предположим, ваш файл называется main.py)
CMD ["python", "voicemusic.py"]
