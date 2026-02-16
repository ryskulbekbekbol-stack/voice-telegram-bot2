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

@app.on_message(filters.command("play") & filters.me)
async def play_music(client, message):
    if len(message.command) < 2:
        return await message.reply("Использование: /play <YouTube URL или запрос>")
    
    query = message.command[1]
    status = await message.reply("🔄 Загружаю...")
    
    try:
        filename = await asyncio.get_event_loop().run_in_executor(None, download_audio, query)
    except Exception as e:
        return await status.edit(f"❌ Ошибка загрузки: {e}")
    
    chat_id = message.chat.id  # всегда берём ID из текущего сообщения
    if not vc.is_connected(chat_id):
        try:
            await vc.join_call(chat_id)
        except Exception as e:
            return await status.edit(f"❌ Не удалось подключиться: {e}")
    
    await vc.play(chat_id, filename)
    await status.edit(f"🎵 Играет: {query}")

app.run()
