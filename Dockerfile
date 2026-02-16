FROM python:3.10-slim

# Устанавливаем компиляторы и заголовки (нужны для сборки некоторых пакетов)
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем файлы зависимостей
COPY requirements.txt .

# Устанавливаем Python-пакеты
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальной код
COPY . .

# Команда запуска (замените на вашу)
CMD ["python", "voicemusic.py"]
