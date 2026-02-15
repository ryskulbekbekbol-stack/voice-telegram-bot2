FROM python:3.11-slim

WORKDIR /app

# Устанавливаем системные зависимости (включая git и libssl-dev)
RUN apt-get update && apt-get install -y \
    gcc \
    build-essential \
    ffmpeg \
    git \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Единая команда без лишних переносов, с --no-cache-dir
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "voicemusic.py"]
