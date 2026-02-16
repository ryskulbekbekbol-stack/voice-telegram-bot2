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

# Проверка ffmpeg
try:
    subprocess.run(['ffmpeg', '-version'], check=True, capture_output=True)
    print("✅ FFmpeg установлен")
except Exception:
    print("⚠️ FFmpeg не найден. Убедитесь, что он установлен в контейнере.")

# ========== ИНИЦИАЛИЗАЦИЯ ==========
app = Client(
    "userbot",
    session_string=SESSION_STRING,
    api_id=API_ID,
    api_hash=API_HASH,
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

# ========== ФУНКЦИЯ СКАЧИВАНИЯ ==========
def download_audio(query):
    """
    Скачивает аудио с YouTube. Использует максимально совместимые настройки.
    """
    print(f"Начинаю скачивание: {query}")
    print(f"Файл cookies.txt существует: {os.path.exists('cookies.txt')}")

    ydl_opts = {
        # Пробуем разные форматы в порядке приоритета
        'format': 'worstaudio/worst',
        'outtmpl': 'audio.%(ext)s',
        'cookiefile': 'cookies.txt',
        'quiet': False,
        'no_warnings': False,
        'ignoreerrors': True,
        'no_color': True,
        'extract_flat': False,
        'force_generic_extractor': False,
        'nocheckcertificate': True,
        'prefer_ffmpeg': True,
        # Добавляем User-Agent чтобы не блокировали
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        # Добавляем заголовки как у браузера
        'headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate',
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Сначала получаем информацию
            info = ydl.extract_info(query, download=False)
            if info is None:
                # Если не получилось, пробуем другой подход
                print("Первая попытка не удалась, пробуем с extract_flat=True...")
                ydl_opts['extract_flat'] = True
                with yt_dlp.YoutubeDL(ydl_opts) as ydl2:
                    info = ydl2.extract_info(query, download=False)
                    if info is None:
                        raise Exception("yt-dlp не смог получить информацию о видео")

            # Теперь скачиваем
            ydl_opts['extract_flat'] = False
            with yt_dlp.YoutubeDL(ydl_opts) as ydl3:
                info = ydl3.extract_info(query, download=True)
                if info is None:
                    raise Exception("yt-dlp вернул None при скачивании")

                filename = ydl3.prepare_filename(info)

                # Если файл не найден, ищем audio.*
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

    try:
        await ensure_vc_started()
    except Exception as e:
        print(f"Ошибка запуска TgCaller: {e}")
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
            print("✅ Подключено")
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

# ========== ОБРАБОТЧИК ОШИБОК ==========
def exception_handler(loop, context):
    print(f"Поймано исключение: {context}")

loop = asyncio.get_event_loop()
loop.set_exception_handler(exception_handler)

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print("🚀 Бот запускается...")
    app.run()
