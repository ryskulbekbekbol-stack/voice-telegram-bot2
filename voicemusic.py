import os
import asyncio
import yt_dlp
import subprocess
import glob
from pyrogram import Client, filters
from tgcaller import TgCaller

# ========== НАСТРОЙКИ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ==========
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")

# Проверка наличия ffmpeg и nodejs
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

# ========== ИНИЦИАЛИЗАЦИЯ КЛИЕНТА И TgCaller ==========
app = Client(
    "userbot",
    session_string=SESSION_STRING,
    api_id=API_ID,
    api_hash=API_HASH,
    in_memory=True  # не храним сессию на диске
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

# ========== ФУНКЦИЯ СКАЧИВАНИЯ АУДИО С YouTube ==========
def download_audio(query):
    print(f"\n=== Начинаю скачивание: {query} ===")
    print(f"cookies.txt существует: {os.path.exists('cookies.txt')}")

    ydl_opts = {
        'format': 'bestaudio*',                     # Лучший аудиоформат
        'outtmpl': 'audio.%(ext)s',                  # Имя файла
        'cookiefile': 'cookies.txt',                 # Куки для авторизации
        'quiet': False,
        'verbose': True,                              # Подробный вывод
        'no_warnings': False,
        'ignoreerrors': True,
        'extract_flat': False,
        'nocheckcertificate': True,
        'prefer_ffmpeg': True,
        'source_address': '91.247.59.86',                  # Принудительный IPv4
        # Пробуем несколько клиентов (web поддерживает куки)
        'extractor_args': {'youtube': {'player_client': ['web', 'android', 'ios', 'tv']}},
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate',
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=True)
            if info is None:
                raise Exception("yt-dlp не смог получить информацию о видео")
            filename = ydl.prepare_filename(info)
            # Если файл не найден (например, расширение изменилось), ищем audio.*
            if not os.path.exists(filename):
                files = glob.glob("audio.*")
                if files:
                    filename = files[0]
                else:
                    raise FileNotFoundError("Не удалось найти скачанный файл")
            print(f"✅ Скачано: {filename}, размер: {os.path.getsize(filename)} байт")
            return filename
    except Exception as e:
        print(f"❌ Ошибка в yt-dlp: {e}")
        raise

# ========== КОМАНДА /play ==========
@app.on_message(filters.command("play") & (filters.group | filters.channel))
async def play_music(client, message):
    if len(message.command) < 2:
        await message.reply("Использование: /play <YouTube URL или запрос>")
        return

    query = message.command[1]
    status = await message.reply("🔄 Загружаю...")

    if not check_deps():
        await status.edit("❌ Отсутствуют ffmpeg или nodejs. Установите их.")
        return

    try:
        # Скачивание в отдельном потоке, чтобы не блокировать асинхронность
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

# ========== КОМАНДА /stop ==========
@app.on_message(filters.command("stop") & (filters.group | filters.channel))
async def stop_music(client, message):
    chat_id = message.chat.id
    if vc.is_connected(chat_id):
        await vc.stop_playback(chat_id)
        await vc.leave_call(chat_id)
        await message.reply("⏹️ Воспроизведение остановлено.")
    else:
        await message.reply("❌ Я не в голосовом чате.")

# ========== ГЛОБАЛЬНЫЙ ОБРАБОТЧИК ИСКЛЮЧЕНИЙ ==========
def exception_handler(loop, context):
    print(f"⚠️ Поймано исключение: {context}")

loop = asyncio.get_event_loop()
loop.set_exception_handler(exception_handler)

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print("🚀 Бот запускается на вашем IP...")
    app.run()
