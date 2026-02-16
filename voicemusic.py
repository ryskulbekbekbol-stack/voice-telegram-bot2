import os
import asyncio
import subprocess
import yt_dlp

from pyrogram import Client, filters
from tgcaller import TgCaller

# ===== Переменные окружения =====
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]

# ===== Проверка ffmpeg =====
try:
    subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    print("✅ ffmpeg установлен")
except Exception as e:
    print("⚠️ ffmpeg не найден, музыка может не играть", e)

# ===== Клиент Pyrogram =====
app = Client(
    "userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

vc = TgCaller(app)
_started = False

async def ensure_started():
    global _started
    if not _started:
        print("▶️ Запуск TgCaller...")
        await vc.start()
        _started = True
        print("✅ TgCaller запущен")

# ===== Функция загрузки музыки с конвертацией =====
async def download_audio(query):
    loop = asyncio.get_event_loop()
    filename = f"track_{os.urandom(4).hex()}.mp3"

    ydl_opts = {
        "format": "bestaudio",
        "outtmpl": filename,
        "noplaylist": True,
        "postprocessors": [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        "quiet": True
    }

    def _dl():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"ytsearch1:{query}"])

    await loop.run_in_executor(None, _dl)

    if not os.path.exists(filename):
        raise Exception("Файл не скачался")

    print("✅ Файл готов:", filename)
    return filename

# ===== Команда /play =====
@app.on_message(filters.command("play") & filters.group)
async def play(_, msg):
    if len(msg.command) < 2:
        await msg.reply("/play название песни")
        return

    query = " ".join(msg.command[1:])
    status_msg = await msg.reply("🔄 Загружаю трек...")

    try:
        file = await download_audio(query)
    except Exception as e:
        await status_msg.edit(f"❌ Ошибка загрузки: {e}")
        return

    await ensure_started()
    chat_id = msg.chat.id

    try:
        if not vc.is_connected(chat_id):
            print("▶️ Подключение к войсу...")
            await vc.join_call(chat_id)
            await asyncio.sleep(3)  # задержка для стабильности
    except Exception as e:
        await status_msg.edit(f"❌ Ошибка подключения: {e}")
        return

    try:
        print("▶️ Воспроизведение...")
        await vc.play(chat_id, file)
        await status_msg.edit(f"🎵 Играет: {query}")
    except Exception as e:
        await status_msg.edit(f"❌ Ошибка воспроизведения: {e}")

# ===== Команда /stop =====
@app.on_message(filters.command("stop") & filters.group)
async def stop(_, msg):
    chat_id = msg.chat.id

    if vc.is_connected(chat_id):
        await vc.stop_playback(chat_id)
        await vc.leave_call(chat_id)
        await msg.reply("⏹ Воспроизведение остановлено")
    else:
        await msg.reply("❌ Я не в голосовом чате")

# ===== Запуск бота =====
print("🚀 Бот стартует...")
app.run()
