import os
import asyncio
import subprocess
import glob
import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatMemberStatus
from tgcaller import TgCaller
import config

# ========== ПРОВЕРКА ЗАВИСИМОСТЕЙ ==========
def check_deps():
    ok = True
    try:
        subprocess.run(['ffmpeg', '-version'], check=True, capture_output=True)
        print("✅ FFmpeg установлен")
    except:
        print("❌ FFmpeg не найден. Установите ffmpeg.")
        ok = False
    try:
        node_v = subprocess.run(['node', '--version'], check=True, capture_output=True, text=True)
        print(f"✅ Node.js установлен: {node_v.stdout.strip()}")
    except:
        print("❌ Node.js не найден. Установите Node.js.")
        ok = False
    return ok

# ========== ИНИЦИАЛИЗАЦИЯ ==========
os.makedirs(config.DOWNLOAD_PATH, exist_ok=True)

app = Client(
    "userbot",
    session_string=config.SESSION_STRING,
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    in_memory=True
)

vc = TgCaller(app)

_vc_started = False

async def ensure_vc_started():
    global _vc_started
    if not _vc_started:
        print("▶️ Запуск TgCaller...")
        await vc.start()
        _vc_started = True
        print("✅ TgCaller запущен")

# ========== ФУНКЦИЯ ПОИСКА НА YOUTUBE ==========
def search_youtube(query: str):
    """Ищет видео на YouTube и возвращает URL первого результата"""
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'default_search': 'ytsearch',
        'source_address': '91.247.59.86',
        'js_runtime': 'node',                       # принудительно используем Node.js
        'extractor_args': {'youtube': {'js_runner': 'node'}},
        'allow_unsupported_runtimes': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)
            if info and info.get('entries'):
                video = info['entries'][0]
                return {
                    'title': video.get('title'),
                    'url': video.get('webpage_url'),
                    'duration': video.get('duration')
                }
    except Exception as e:
        print(f"Ошибка YouTube поиска: {e}")
    return None

# ========== ФУНКЦИЯ СКАЧИВАНИЯ АУДИО ==========
def download_audio_from_youtube(url: str):
    """Скачивает аудио с YouTube, конвертирует в MP3, возвращает имя файла"""
    ydl_opts = {
        'format': 'bestaudio*',
        'outtmpl': os.path.join(config.DOWNLOAD_PATH, '%(title)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'js_runtime': 'node',
        'extractor_args': {'youtube': {'js_runner': 'node'}},
        'allow_unsupported_runtimes': True,
        'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,  # опционально
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        # после конвертации расширение .mp3
        filename = filename.rsplit('.', 1)[0] + '.mp3'
        return filename

# ========== КОМАНДА /play (только для вас) ==========
@app.on_message(filters.command("play") & filters.me)
async def play_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.edit("❌ Укажите название трека")
        return

    query = ' '.join(message.command[1:])
    status = await message.edit(f"🔍 Ищу: {query}")

    # Проверка зависимостей
    if not check_deps():
        await status.edit("❌ Отсутствуют ffmpeg или nodejs")
        return

    # Поиск на YouTube
    yt_info = search_youtube(query)
    if not yt_info:
        await status.edit("❌ Ничего не найдено")
        return

    await status.edit(f"⬇️ Скачиваю: {yt_info['title']}")

    try:
        filename = await asyncio.get_event_loop().run_in_executor(None, download_audio_from_youtube, yt_info['url'])
    except Exception as e:
        await status.edit(f"❌ Ошибка загрузки: {e}")
        return

    # Запускаем голосовой модуль и подключаемся к чату
    await ensure_vc_started()
    chat_id = message.chat.id

    try:
        if not vc.is_connected(chat_id):
            await vc.join_call(chat_id)
    except Exception as e:
        await status.edit(f"❌ Не удалось подключиться к голосовому чату: {e}")
        os.remove(filename)
        return

    # Воспроизводим
    try:
        await vc.play(chat_id, filename)
        await status.edit(f"🎵 Сейчас играет: {yt_info['title']}")
    except Exception as e:
        await status.edit(f"❌ Ошибка воспроизведения: {e}")
    finally:
        # Удаляем файл через некоторое время (можно добавить задержку)
        os.remove(filename)

# ========== КОМАНДА /stop ==========
@app.on_message(filters.command("stop") & filters.me)
async def stop_command(client: Client, message: Message):
    chat_id = message.chat.id
    if vc.is_connected(chat_id):
        await vc.stop_playback(chat_id)
        await vc.leave_call(chat_id)
        await message.edit("⏹️ Воспроизведение остановлено")
    else:
        await message.edit("❌ Я не в голосовом чате")

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print("🚀 YouTube юзербот запускается...")
    app.run()
