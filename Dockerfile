FROM python:3.11-slim

# Устанавливаем системные пакеты: ffmpeg, nodejs, npm, curl
RUN apt-get update && apt-get install -y \
    curl \
    ffmpeg \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Проверка установки (будет в логах сборки)
RUN node --version && npm --version && ffmpeg -version

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "voicemusic.py"]
