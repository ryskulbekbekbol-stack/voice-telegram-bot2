import os
import asyncio
import yt_dlp
import subprocess
from pyrogram import Client, filters
from pyrogram.handlers import RawUpdateHandler
from tgcaller import TgCaller

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")

# Проверка ffmpeg (для отладки)
try:
    subprocess.run(['ffmpeg', '-version'], check=True, capture_output=True)
    print("✅ FFmpeg установлен")
except Exception as e:
    print("❌ FFmpeg не найден:", e)

app = Client("userbot", session_string=SESSION_STRING, api_id=API_ID, api_hash=API_HASH, in_memory=True)
vc = TgCaller(app)

# Флаг, что TgCaller запущен
vc_started = False

async def ensure_vc_started():
    global vc_started
    if not vc_started:
        print("▶️ Запуск TgCaller...")
        await vc.start()
        vc_started = True
        print("✅ TgCaller запущен")

def download_audio(query):
    print(f"Начинаю скачивание: {query}")
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'audio.%(ext)s',
        'quiet': False,
        'no_warnings': False,
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
        print(f"✅ Скачано: {filename}, размер: {os.path.getsize(filename)}")
        return filename

@app.on_message(filters.command("play") & (filters.group | filters.channel))
async def play_music(client, message):
    print(f"Команда play в чате {message.chat.id} от {message.from_user.id}")
    if len(message.command) < 2:
        await message.reply("Использование: /play <YouTube URL или запрос>")
        return

    query = message.command[1]
    status = await message.reply("🔄 Загружаю...")

    try:
        filename = await asyncio.get_event_loop().run_in_executor(None, download_audio, query)
    except Exception as e:
        print(f"Ошибка загрузки: {e}")
        await status.edit(f"❌ Ошибка загрузки: {e}")
        return

    # Убедимся, что TgCaller запущен
    try:
        await ensure_vc_started()
    except Exception as e:
        print(f"Ошибка запуска TgCaller: {e}")
        await status.edit("❌ Ошибка инициализации TgCaller")
        return

    chat_id = message.chat.id
    try:
        if not vc.is_connected(chat_id):
            print(f"Подключаюсь к чату {chat_id}")
            await vc.join_call(chat_id)
            print("✅ Подключено")
        else:
            print("Уже подключено")
    except Exception as e:
        print(f"Ошибка подключения: {e}")
        await status.edit(f"❌ Не удалось подключиться: {e}")
        try:
            os.remove(filename)
        except:
            pass
        return

    try:
        print(f"Воспроизвожу {filename}")
        await vc.play(chat_id, filename)
        print("✅ Воспроизведение запущено")
        await status.edit(f"🎵 Сейчас играет: {query}")
    except Exception as e:
        print(f"Ошибка воспроизведения: {e}")
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
        await message.reply("⏹️ Остановлено.")
    else:
        await message.reply("❌ Не в голосовом чате.")

# Запускаем TgCaller после старта клиента
@app.on_start()
async def start_vc(client):
    await ensure_vc_started()

app.run()
