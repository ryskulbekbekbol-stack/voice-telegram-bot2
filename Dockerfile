FROM python:3.11-slim

# Устанавливаем системные зависимости для компиляции и работы с аудио/видео
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

# Обновляем CMake до более новой версии (если требуется)
# Можно пропустить, если встроенный cmake подходит. Но для надёжности:
RUN wget -qO- "https://github.com/Kitware/CMake/releases/download/v3.28.3/cmake-3.28.3-linux-x86_64.tar.gz" | tar --strip-components=1 -xz -C /usr/local

WORKDIR /app

# Копируем requirements.txt и обновляем pip
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip

# Пытаемся установить зависимости (с подробным выводом для отладки)
RUN pip install --no-cache-dir -v -r requirements.txt

# Копируем остальной код
COPY . .

# Команда запуска (предполагаем, что ваш файл называется main.py)
CMD ["python", "voicemusic.py"]
