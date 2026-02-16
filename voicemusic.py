import os
import asyncio
import yt_dlp
import subprocess
import glob
import random
from pyrogram import Client, filters
from tgcaller import TgCaller

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")

# Список прокси (замените на рабочие, если нужно)
PROXY_LIST = [
    'http://65.108.159.129',
    'http://216.229.112.25',
    'http://147.75.34.105',
    'http://94.176.3.109',
]

def check_dependencies():
    deps_ok = True
    try:
        subprocess.run(['ffmpeg', '-version'], check=True, capture_output=True)
        print("✅ FFmpeg установлен")
    except:
        print("❌ FFmpeg не найден")
        deps_ok = False
    try:
        node_v = subprocess.run(['node', '--version'], check=True, capture_output=True, text=True)
        print(f"✅ Node.js установлен: {node_v.stdout.strip()}")
        # Дополнительно выведем путь
        node_path = subprocess.run(['which', 'node'], capture_output=True, text=True)
        print(f"   Путь: {node_path.stdout.strip()}")
    except:
        print("❌ Node.js не найден")
        deps_ok = False
    return deps_ok

app = Client("userbot", session_string=SESSION_STRING, api_id=API_ID, api_hash=API_HASH, in_memory=True)
vc = TgCaller(app)

_vc_started = False

async def ensure_vc_started():
    global _vc_started
    if not _vc_started:
        print("▶️ Запуск TgCaller...")
        await vc.start()
        _vc_started = True
        print("✅ TgCaller запущен")

def download_audio(query):
    print(f"\n=== Начинаю скачивание: {query} ===")

    ydl_opts = {
        'format': 'bestaudio*',                     # или 'worstaudio', если нужно
        'outtmpl': 'audio.%(ext)s',
        'cookiefile': 'cookies.txt',
        'quiet': False,
        'verbose': True,
        'no_warnings': False,
        'ignoreerrors': True,
        'extract_flat': False,
        'nocheckcertificate': True,
        'prefer_ffmpeg': True,
        'source_address': '0.0.0.0',
        # Принудительно указываем использовать Node.js
        'js_runtime': 'node',
        # В extractor_args добавляем js_runner
        'extractor_args': {'youtube': {'player_client': ['web', 'android', 'ios', 'tv'], 'js_runner': 'node'}},
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate',
        }
    }

    # Пробуем прокси (если есть)
    if PROXY_LIST:
        random.shuffle(PROXY_LIST)
        for proxy in PROXY_LIST:
            print(f"🔄 Пробую прокси: {proxy}")
            ydl_opts['proxy'] = proxy
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(query, download=True)
                    if info is None:
                        raise Exception("yt-dlp вернул None")
                    filename = ydl.prepare_filename(info)
                    if not os.path.exists(filename):
                        files = glob.glob("audio.*")
                        if files:
                            filename = files[0]
                        else:
                            raise FileNotFoundError("Не удалось найти скачанный файл")
                    print(f"✅ Скачано: {filename}, размер: {os.path.getsize(filename)} байт (прокси: {proxy})")
                    return filename
            except Exception as e:
                print(f"❌ Прокси {proxy} не сработал: {e}")
                continue

    # Если прокси не сработали или их нет, пробуем без прокси
    print("🔄 Пробую без прокси...")
    ydl_opts.pop('proxy', None)
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=True)
            if info is None:
                raise Exception("yt-dlp вернул None")
            filename = ydl.prepare_filename(info)
            if not os.path.exists(filename):
                files = glob.glob("audio.*")
                if files:
                    filename = files[0]
                else:
                    raise FileNotFoundError("Не удалось найти скачанный файл")
            print(f"✅ Скачано без прокси: {filename}, размер: {os.path.getsize(filename)} байт")
            return filename
    except Exception as e:
        print(f"❌ Ошибка без прокси: {e}")
        raise

@app.on_message(filters.command("play") & (filters.group | filters.channel))
async def play_music(client, message):
    if len(message.command) < 2:
        await message.reply("Использование: /play <YouTube URL или запрос>")
        return

    query = message.command[1]
    status = await message.reply("🔄 Загружаю...")

    if not check_dependencies():
        await status.edit("❌ Отсутствуют системные зависимости (ffmpeg/nodejs).")
        return

    try:
        filename = await asyncio.get_event_loop().run_in_executor(None, download_audio, query)
    except Exception as e:
        await status.edit(f"❌ Ошибка загрузки: {e}")
        return

    try:
        await ensure_vc_started()
    except Exception as e:
        await status.edit("❌ Ошибка инициализации голосового модуля")
        try:
            os.remove(filename)
        except:
            pass
        return

    chat_id = message.chat.id

    try:
        if not vc.is_connected(chat_id):
            print(f"Подключаюсь к чату {chat_id}")
            await vc.join_call(chat_id)
    except Exception as e:
        await status.edit(f"❌ Не удалось подключиться: {e}")
        try:
            os.remove(filename)
        except:
            pass
        return

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

def exception_handler(loop, context):
    print(f"⚠️ Поймано исключение: {context}")

loop = asyncio.get_event_loop()
loop.set_exception_handler(exception_handler)

if __name__ == "__main__":
    print("🚀 Бот запускается...")
    app.run()
