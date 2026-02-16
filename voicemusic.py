import os
from pyrogram import Client, filters
from tgcaller import TgCaller
from tgcaller.advanced import YouTubeStreamer

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")

app = Client("userbot", session_string=SESSION_STRING, api_id=API_ID, api_hash=API_HASH)
vc = TgCaller(app)
yt = YouTubeStreamer(vc)

@app.on_message(filters.command("play") & filters.me)
async def play_music(client, message):
    if len(message.command) < 2:
        return await message.reply("Использование: /play <название или URL>")
    
    query = message.command[1]
    
    if not vc.is_connected(message.chat.id):
        await vc.join_call(message.chat.id)
    
    # Поддерживает и YouTube URL, и поиск
    await yt.play_youtube_url(message.chat.id, query)
    await message.reply(f"🎵 Играет: {query}")

app.run()
