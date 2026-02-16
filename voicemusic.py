import os
import yt_dlp
from pyrogram import Client, filters
from tgcaller import TgCaller

app = Client("userbot", session_string=os.environ["SESSION_STRING"], 
             api_id=int(os.environ["API_ID"]), api_hash=os.environ["API_HASH"])
vc = TgCaller(app)

def download_audio(url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'audio.%(ext)s',
        'quiet': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        # yt-dlp может добавить расширение .webm или .m4a
        if not os.path.exists(filename):
            import glob
            files = glob.glob("audio.*")
            if files:
                filename = files[0]
        return filename

@app.on_message(filters.command("play") & filters.me)
async def play_music(client, message):
    if len(message.command) < 2:
        return await message.reply("Использование: /play <YouTube URL>")
    
    url = message.command[1]
    status = await message.reply("🔄 Загружаю...")
    
    try:
        filename = await asyncio.get_event_loop().run_in_executor(None, download_audio, url)
    except Exception as e:
        return await status.edit(f"❌ Ошибка загрузки: {e}")
    
    if not vc.is_connected(message.chat.id):
        await vc.join_call(message.chat.id)
    
    await vc.play(message.chat.id, filename)
    await status.edit(f"🎵 Играет: {url}")

app.run()
