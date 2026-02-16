import os
import asyncio
import subprocess
import glob
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
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
        print("❌ FFmpeg не найден")
        ok = False
    try:
        node_v = subprocess.run(['node', '--version'], check=True, capture_output=True, text=True)
        print(f"✅ Node.js установлен: {node_v.stdout.strip()}")
    except:
        print("❌ Node.js не найден")
        ok = False
    return ok

# ========== ИНИЦИАЛИЗАЦИЯ ==========
os.makedirs(config.DOWNLOAD_PATH, exist_ok=True)

# Подключаемся к Telegram как юзер
app = Client(
    "userbot",
    session_string=config.SESSION_STRING,
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    in_memory=True
)

# Подключаем голосовой модуль
vc = TgCaller(app)

# Подключаемся к Spotify API
sp = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=config.SPOTIFY_CLIENT_ID,
        client_secret=config.SPOTIFY_CLIENT_SECRET
    )
)

# Флаг запуска TgCaller
_vc_started = False

async def ensure_vc_started():
    global _vc_started
    if not _vc_started:
        print("▶️ Запуск TgCaller...")
        await vc.start()
        _vc_started = True
        print("✅ TgCaller запущен")

# ========== ФУНКЦИИ ПОИСКА ==========
def search_spotify(query: str):
    """Ищет треки в Spotify и возвращает первый результат"""
    try:
        results = sp.search(q=query, type='track', limit=1)
        if results['tracks']['items']:
            item = results['tracks']['items'][0]
            return {
                'name': item['name'],
                'artist': item['artists'][0]['name'],
                'duration': item['duration_ms'] // 1000,
                'url': item['external_urls']['spotify']
            }
    except Exception as e:
        print(f"Ошибка Spotify: {e}")
    return None

def search_youtube(query: str):
    """Ищет на YouTube и возвращает информацию для скачивания"""
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'default_search': 'ytsearch',
        'source_address': '0.0.0.0'
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
        print(f"Ошибка YouTube: {e}")
    return None

def download_audio_from_youtube(url: str):
    """Скачивает аудио с YouTube и возвращает имя файла"""
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
        'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,  # опционально
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        # конвертируем в mp3 (если не был mp3)
        filename = filename.rsplit('.', 1)[0] + '.mp3'
        return filename

# ========== КОМАНДЫ (доступны только вам) ==========
@app.on_message(filters.command("play") & filters.me)
async def play_command(client: Client, message: Message):
    """Использование: /play <название трека>"""
    if len(message.command) < 2:
        await message.edit("❌ Укажите название трека")
        return

    query = ' '.join(message.command[1:])
    status = await message.edit("🔍 Ищу на Spotify...")

    # Сначала ищем в Spotify
    spotify_track = search_spotify(query)
    if spotify_track:
        search_query = f"{spotify_track['name']} {spotify_track['artist']}"
        await status.edit(f"🎵 Нашёл на Spotify: {spotify_track['name']} - {spotify_track['artist']}\n🔍 Ищу на YouTube...")
    else:
        search_query = query
        await status.edit("🔍 Ищу прямо на YouTube...")

    # Ищем на YouTube
    yt_info = search_youtube(search_query)
    if not yt_info:
        await status.edit("❌ Ничего не найдено")
        return

    await status.edit(f"⬇️ Скачиваю: {yt_info['title']}")

    try:
        # Скачиваем аудио
        filename = await asyncio.get_event_loop().run_in_executor(None, download_audio_from_youtube, yt_info['url'])
    except Exception as e:
        await status.edit(f"❌ Ошибка загрузки: {e}")
        return

    # Запускаем голосовой модуль
    if not check_deps():
        await status.edit("❌ Отсутствуют ffmpeg или nodejs")
        os.remove(filename)
        return

    await ensure_vc_started()

    chat_id = message.chat.id
    # Подключаемся к голосовому чату
    try:
        if not vc.is_connected(chat_id):
            await vc.join_call(chat_id)
    except Exception as e:
        await status.edit(f"❌ Не удалось подключиться: {e}")
        os.remove(filename)
        return

    # Воспроизводим
    try:
        await vc.play(chat_id, filename)
        await status.edit(f"🎵 Сейчас играет: {yt_info['title']}")
    except Exception as e:
        await status.edit(f"❌ Ошибка воспроизведения: {e}")
    finally:
        # Удаляем файл после окончания (можно добавить задержку, но для простоты удалим сейчас)
        # В реальности нужно дождаться окончания трека или добавить событие.
        # Пока удалим, чтобы не засорять диск.
        os.remove(filename)

@app.on_message(filters.command("stop") & filters.me)
async def stop_command(client: Client, message: Message):
    chat_id = message.chat.id
    if vc.is_connected(chat_id):
        await vc.stop_playback(chat_id)
        await vc.leave_call(chat_id)
        await message.edit("⏹️ Воспроизведение остановлено")
    else:
        await message.edit("❌ Я не в голосовом чате")

@app.on_message(filters.command("spotify") & filters.me)
async def spotify_search_command(client: Client, message: Message):
    """Ищет трек в Spotify и возвращает ссылку (без скачивания)"""
    if len(message.command) < 2:
        await message.edit("Укажите название")
        return
    query = ' '.join(message.command[1:])
    status = await message.edit("🔍 Ищу на Spotify...")
    track = search_spotify(query)
    if track:
        text = f"🎵 **{track['name']}**\n👤 {track['artist']}\n💿 [Слушать на Spotify]({track['url']})"
        await status.edit(text, disable_web_page_preview=True)
    else:
        await status.edit("❌ Не найдено")

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print("🚀 Spotify юзербот запускается...")
    app.run()
