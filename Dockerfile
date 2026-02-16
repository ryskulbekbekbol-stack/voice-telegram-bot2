FROM python:3.11-slim

# Устанавливаем системные зависимости: компиляторы, CMake, библиотеки для аудио/видео, git
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    ninja-build \
    python3-dev \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libswresample-dev \
    libopus-dev \
    libvpx-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем requirements и обновляем pip
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Устанавливаем зависимости с подробным выводом (для отладки)
RUN pip install --no-cache-dir -v -r requirements.txt

# Копируем остальной код
COPY . .

# Команда запуска (предполагаем, что ваш главный файл называется main.py)
CMD ["python", "voicemusic.py"]
