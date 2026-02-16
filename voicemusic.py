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

# Проверка наличия ffmpeg
try:
    subprocess.run(['ffmpeg', '-version'], check=True, capture_output=True)
    print("✅ FFmpeg установлен")
except Exception:
    print("⚠️ FFmpeg не найден. Убедитесь, что он установлен в контейнере.")

# ========== ИНИЦИАЛИЗАЦИЯ КЛИЕНТА И TgCaller ==========
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

# ========== ФУНКЦИЯ СКАЧИВАНИЯ АУДИО С YouTube ==========
def download_audio(query):
    """
    Скачивает аудио с YouTube. Использует формат worstaudio (самый надёжный).
    """
    print(f"Начинаю скачивание: {query}")
    print("Проверка наличия cookies.txt:", os.path.exists('cookies.txt'))

    ydl_opts = {
        'format': 'worstaudio/worst',          # самый надёжный формат
        'outtmpl': 'audio.%(ext)s',
        'cookiefile': 'cookies.txt',           # файл с куками
        'quiet': False,                         # подробный вывод для отладки
        'no_warnings': False,
        'extract_flat': False,
        'force_generic_extractor': True,        # пробовать общий извлекатель
        'ignoreerrors': True,                    # не останавливаться при ошибках
        'no_color': True,
        'prefer_ffmpeg': True,                   # использовать ffmpeg для слияния
        'keepvideo': False,                       # не сохранять видео
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=True)
            if info is None:
                raise Exception("yt-dlp вернул None")

            filename = ydl.prepare_filename(info)

            # Если файл не найден (например, расширение изменилось), ищем audio.*
            if not os.path.exists(filename):
                files = glob.glob("audio.*")
                if files:
                    filename = files[0]
                else:
                    # Попробуем получить имя из info
                    if 'requested_downloads' in info and info['requested_downloads']:
                        filename = info['requested_downloads'][0].get('filepath', '')
                    if not filename or not os.path.exists(filename):
                        raise FileNotFoundError("Не удалось найти скачанный файл")

            print(f"✅ Скачано: {filename}, размер: {os.path.getsize(filename)} байт")
            return filename

    except Exception as e:
        print(f"❌ Ошибка в yt-dlp: {e}")
        raise

# ========== ОБРАБОТЧИК КОМАНДЫ /play ==========
@app.on_message(filters.command("play") & (filters.group | filters.channel))
async def play_music(client, message):
    print(f"Команда play в чате {message.chat.id} от {message.from_user.id}")

    if len(message.command) < 2:
        await message.reply("Использование: /play <YouTube URL или запрос>")
        return

    query = message.command[1]
    status = await message.reply("🔄 Загружаю...")

    # 1. Скачиваем аудио
    try:
        filename = await asyncio.get_event_loop().run_in_executor(None, download_audio, query)
    except Exception as e:
        print(f"Ошибка загрузки: {e}")
        await status.edit(f"❌ Ошибка загрузки: {e}")
        return

    # 2. Убеждаемся, что TgCaller запущен
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

    # 3. Подключаемся к голосовому чату, если ещё не подключены
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

    # 4. Воспроизводим
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

# ========== ОБРАБОТЧИК КОМАНДЫ /stop ==========
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
    print(f"Поймано исключение в цикле событий: {context}")

loop = asyncio.get_event_loop()
loop.set_exception_handler(exception_handler)

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print("🚀 Бот запускается...")
    app.run()
