FROM python:3.11-slim

WORKDIR /app

# Устанавливаем системные зависимости и ffmpeg
RUN apt-get update && apt-get install -y \
    gcc \
    build-essential \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# Замените "bot.py" на имя вашего главного файла
CMD ["python", "voicemusic.py"]
