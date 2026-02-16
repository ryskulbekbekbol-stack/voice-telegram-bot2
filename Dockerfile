FROM marshalx/tgcalls:latest

WORKDIR /app

# Копируем requirements.txt (без git-ссылки на tgcalls!)
COPY requirements.txt .

# Устанавливаем остальные Python-зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код проекта
COPY . .

# Команда запуска (замените main.py на имя вашего файла)
CMD ["python", "voicemusic.py"]
