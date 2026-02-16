import os
import asyncio
import yt_dlp
from pyrogram import Client, filters
from pyrogram.errors import PeerIdInvalid, ChatAdminRequired
from tgcaller import TgCaller

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")

# Глобальный обработчик непойманных исключений (чтобы бот не падал)
def exception_handler(loop, context):
    print(f"Поймано исключение в цикле событий: {context}")

app = Client(
    "userbot",
    session_string=SESSION_STRING,
    api_id=API_ID,
    api_hash=API_HASH,
    in_memory=True  # не сохраняет кэш на диск, чтобы избежать старых ID
)
vc = TgCaller(app)

def download_audio(query):
    """Скачивает аудио с YouTube, возвращает имя файла"""
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'audio.%(ext)s',
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=True)
        filename = ydl.prepare_filename(info)
        if not os.path.exists(filename):
            import glob
            files = glob.glob("audio.*")
            if files:
                filename = files[0]
            else:
                raise FileNotFoundError("Не удалось найти скачанный файл")
        return filename

@app.on_message(filters.command("play") & (filters.group | filters.channel))
async def play_music(client, message):
    if len(message.command) < 2:
        await message.reply("Использование: /play <YouTube URL или запрос>")
        return

    query = message.command[1]
    status = await message.reply("🔄 Загружаю...")

    try:
        # Скачивание в отдельном потоке, чтобы не блокировать асинхронность
        filename = await asyncio.get_event_loop().run_in_executor(None, download_audio, query)
    except Exception as e:
        await status.edit(f"❌ Ошибка загрузки: {e}")
        return

    chat_id = message.chat.id  # всегда свежий ID из текущего чата

    # Подключаемся к голосовому чату, если ещё не подключены
    try:
        if not vc.is_connected(chat_id):
            await vc.join_call(chat_id)
    except Exception as e:
        await status.edit(f"❌ Не удалось подключиться: {e}")
        try:
            os.remove(filename)
        except:
            pass
        return

    # Воспроизводим
    try:
        await vc.play(chat_id, filename)
        await status.edit(f"🎵 Сейчас играет: {query}")
    except Exception as e:
        await status.edit(f"❌ Ошибка воспроизведения: {e}")
        try:
            os.remove(filename)
        except:
            pass

@app.on_message(filters.command("stop") & (filters.group | filters.channel))
async def stop_music(client, message):
    chat_id = message.chat.id
    if vc.is_connected(chat_id):
        await vc.stop_playback(chat_id)
        await vc.leave_call(chat_id)
        await message.reply("⏹️ Воспроизведение остановлено.")
    else:
        await message.reply("❌ Я не в голосовом чате.")

# Устанавливаем глобальный обработчик исключений для asyncio (чтобы логировать, но не падать)
loop = asyncio.get_event_loop()
loop.set_exception_handler(exception_handler)

app.run()
