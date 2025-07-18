"""
Hitmo Downloader - Поиск и скачивание музыки с hitmotop.com
"""
version = "1.2"
commands = {
    "hitmo": "поиск трека"
}
import os
import tempfile
import asyncio
from telethon import events
import aiohttp
from bs4 import BeautifulSoup

class HitmoParser:
    MAIN_LINK = "https://rus.hitmotop.com/"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    def __init__(self):
        self.res_link = self.MAIN_LINK
        self.track_list = []

    def find_song(self, song_name: str) -> str:
        """Поиск трека по названию"""
        query = "+".join(song_name.split())
        self.res_link = f"{self.MAIN_LINK}search?q={query}"
        return self.res_link

    async def get_songs(self, link: str) -> list:
        """Асинхронное получение списка треков"""
        self.track_list = []
        
        async with aiohttp.ClientSession(headers=self.HEADERS) as session:
            async with session.get(link) as response:
                if response.status != 200:
                    return []
                
                html = await response.text()
                bs = BeautifulSoup(html, "html.parser")
                tracks = bs.find_all("li", {"class": "tracks__item"})
                
                for track in tracks:
                    try:
                        track_title = track.find("div", {"class": "track__title"}).text.strip()
                        track_artist = track.find("div", {"class": "track__desc"}).text.strip()
                        track_length = track.find("div", {"class": "track__fulltime"}).text.strip()
                        track_download_link = track.find("a", {"class": "track__download-btn"})['href']

                        self.track_list.append({
                            "title": track_title,
                            "artist": track_artist,
                            "length": track_length,
                            "download_link": track_download_link
                        })
                    except Exception:
                        continue
        
        return self.track_list

async def on_load(client, prefix):
    handlers = []
    hitmo = HitmoParser()
    
    @client.on(events.NewMessage(pattern=f'^{prefix}hitmo(?: |$)(.*)', outgoing=True))
    async def hitmo_handler(event):
        """Поиск треков на Hitmo"""
        query = event.pattern_match.group(1).strip()
        if not query:
            await event.edit(f"❌ Укажите название трека.\nПример: `{prefix}hitmo трек`")
            return

        try:
            search_url = hitmo.find_song(query)
            tracks = await hitmo.get_songs(search_url)
            
            if not tracks:
                await event.edit("❌ Ничего не найдено")
                return

            response = "🎵 Найденные треки:\n\n"
            for i, track in enumerate(tracks[:10], 1):
                response += f"{i}. {track['artist']} - {track['title']} ({track['length']})\n"
            response += f"\nВыберите номер для скачивания: `{prefix}hitmodl номер`"
            
            await event.edit(response)
        except Exception as e:
            await event.edit(f"❌ Ошибка: {str(e)}")

    handlers.append(hitmo_handler)
    
    @client.on(events.NewMessage(pattern=f'^{prefix}hitmodl(?: |$)(\d+)', outgoing=True))
    async def hitmodl_handler(event):
        """Скачивание выбранного трека"""
        try:
            track_num = int(event.pattern_match.group(1)) - 1
            if not hasattr(hitmo, 'track_list') or track_num < 0 or track_num >= len(hitmo.track_list):
                await event.edit("❌ Неверный номер трека")
                return

            track = hitmo.track_list[track_num]
            await event.edit(f"⬇️ Скачиваю {track['artist']} - {track['title']}...")

            # Создаем временный файл
            with tempfile.NamedTemporaryFile(prefix="hitmo_", suffix=".mp3", delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            # Асинхронное скачивание
            async with aiohttp.ClientSession(headers=HitmoParser.HEADERS) as session:
                async with session.get(track['download_link']) as response:
                    if response.status == 200:
                        with open(tmp_path, 'wb') as f:
                            while True:
                                chunk = await response.content.read(8192)
                                if not chunk:
                                    break
                                f.write(chunk)
            
            # Отправка файла с индикацией загрузки
            upload_task = client.send_file(
                event.chat_id,
                tmp_path,
                caption=f"🎧 {track['artist']} - {track['title']}",
                reply_to=event.reply_to_msg_id
            )
            
            # Параллельное удаление файла после отправки
            try:
                await upload_task
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                await event.delete()
                
        except Exception as e:
            await event.edit(f"❌ Ошибка при скачивании: {str(e)}")
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    handlers.append(hitmodl_handler)
    
    return handlers