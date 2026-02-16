FROM python:3.11-slim

# Устанавливаем ffmpeg и Node.js через apt (проверяем пути)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Проверка: выводим версию и путь Node.js (будет в логах сборки)
RUN node --version && which node && npm --version && ffmpeg -version

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "voicemusic.py"]
