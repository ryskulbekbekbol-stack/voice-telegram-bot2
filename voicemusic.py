import os
import asyncio
import yt_dlp
from pyrogram import Client, filters
from tgcaller import TgCaller

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")

app = Client("userbot", session_string=SESSION_STRING, api_id=API_ID, api_hash=API_HASH)
vc = TgCaller(app)

def download_audio(query):
    """Скачивает аудио с YouTube и возвращает имя файла"""
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'audio.%(ext)s',
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=True)
        filename = ydl.prepare_filename(info)
        # Если файл не найден, ищем по маске audio.*
        if not os.path.exists(filename):
            import glob
            files = glob.glob("audio.*")
            if files:
                filename = files[0]
            else:
                raise FileNotFoundError("Не удалось найти скачанный файл")
        return filename

@app.on_message(filters.command("play") & filters.me)
async def play_music(client, message):
    if len(message.command) < 2:
        return await message.reply("Использование: /play <YouTube URL или запрос>")
    
    query = message.command[1]
    status = await message.reply("🔄 Загружаю...")
    
    try:
        # Скачивание в отдельном потоке, чтобы не блокировать асинхронность
        filename = await asyncio.get_event_loop().run_in_executor(None, download_audio, query)
    except Exception as e:
        return await status.edit(f"❌ Ошибка загрузки: {e}")
    
    # Подключаемся к голосовому чату, если ещё не подключены
    if not vc.is_connected(message.chat.id):
        try:
            await vc.join_call(message.chat.id)
        except Exception as e:
            return await status.edit(f"❌ Не удалось подключиться: {e}")
    
    # Воспроизводим
    await vc.play(message.chat.id, filename)
    await status.edit(f"🎵 Играет: {query}")
    
    # Можно добавить удаление файла после воспроизведения (но это сложнее, требует событий)
    # Пока оставим как есть – файл останется, но при следующем запросе перезапишется

app.run()
