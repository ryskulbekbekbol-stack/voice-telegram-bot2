import os
import asyncio
import aiohttp
import subprocess
from pyrogram import Client, filters
from tgcaller import TgCaller

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")

# Проверка ffmpeg
try:
    subprocess.run(['ffmpeg', '-version'], check=True, capture_output=True)
    print("✅ FFmpeg установлен")
except:
    print("⚠️ FFmpeg не найден, но попробуем работать без него (не получится)")

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

# ========== ФУНКЦИЯ СКАЧИВАНИЯ ЧЕРЕЗ API ==========
async def download_audio_api(query):
    """
    Использует внешний бесплатный API для конвертации YouTube в аудио.
    """
    print(f"Начинаю скачивание через API: {query}")

    # Формируем URL для API (ytdl.uno)
    api_url = f"https://api.ytdl.uno/download"
    params = {
        'url': query,
        'format': 'mp3',
        'quality': '128'
    }

    async with aiohttp.ClientSession() as session:
        try:
            # Отправляем запрос к API
            async with session.get(api_url, params=params, timeout=60) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(f"API вернул ошибку {resp.status}: {text[:100]}")

                # Получаем имя файла из заголовка Content-Disposition (если есть)
                content_disp = resp.headers.get('Content-Disposition', '')
                if 'filename=' in content_disp:
                    filename = content_disp.split('filename=')[-1].strip('"')
                else:
                    filename = f"audio_{os.urandom(4).hex()}.mp3"

                # Сохраняем файл
                with open(filename, 'wb') as f:
                    while True:
                        chunk = await resp.content.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)

                file_size = os.path.getsize(filename)
                print(f"✅ Скачано через API: {filename}, размер: {file_size} байт")
                return filename

        except Exception as e:
            print(f"❌ Ошибка API: {e}")
            raise

# ========== КОМАНДА /play ==========
@app.on_message(filters.command("play") & (filters.group | filters.channel))
async def play_music(client, message):
    if len(message.command) < 2:
        await message.reply("Использование: /play <YouTube URL>")
        return

    query = message.command[1]
    status = await message.reply("🔄 Загружаю через API...")

    try:
        filename = await download_audio_api(query)
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

if __name__ == "__main__":
    print("🚀 Бот запускается (через API)...")
    app.run()
