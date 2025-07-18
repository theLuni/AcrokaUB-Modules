"""
модуль для работы с Yandex.Music
"""

version = "2.4"

commands = {
    "ym": "Текущий трек (аудио)",
    "ymb": "Текущий трек (баннер)",
    "ylike": "Лайкнуть трек",
    "ydislike": "Дизлайкнуть трек",
    "settoken": "установить яндекс токен"
}
# system_requires: libjpeg-turbo
# requires: yandex-music, pillow, requests, aiohttp
import aiohttp
import asyncio
import io
import json
import logging
import random
import requests
import string
import time
import yandex_music
import textwrap
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from telethon import events, types
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)
executor = ThreadPoolExecutor(max_workers=4)

# Глобальные переменные
YM_TOKEN = None
YM_CLIENT = None
CACHE = {}

async def on_load(client, prefix):
    handlers = []
    global YM_TOKEN, YM_CLIENT

    async def get_cached_now_playing():
        if 'now_playing' in CACHE and (time.time() - CACHE['last_update']) < 5:
            return CACHE['now_playing']
        now = await get_now_playing(YM_TOKEN, YM_CLIENT)
        if now:
            CACHE['now_playing'] = now
            CACHE['last_update'] = time.time()
        return now

    # Команда .ym - Получить текущий трек (аудио)
    @client.on(events.NewMessage(pattern=f'^{prefix}ym$', outgoing=True))
    async def ym_handler(event):
        if not YM_CLIENT:
            return await event.edit("<b>❌ Токен не установлен!</b> Используйте <code>.settoken ваш_токен</code>", parse_mode='html')
        
        try:
            msg = await event.edit("<i>⚡ Получаю информацию о треке...</i>", parse_mode='html')
            
            now = await get_cached_now_playing()
            if not now:
                return await msg.edit("<b>❌ Сейчас ничего не играет</b>", parse_mode='html')
            
            track_info = format_track_info(now)
            await msg.edit(track_info + "\n<i>⚡ Загружаю трек...</i>", parse_mode='html')
            
            # Параллельная загрузка аудио
            audio_data = await asyncio.get_event_loop().run_in_executor(
                executor,
                lambda: requests.get(now["track"]["download_link"], timeout=10).content
            )
            
            audio = io.BytesIO(audio_data)
            audio.name = f"{now['track']['title']}.mp3"
            
            await msg.delete()
            await event.reply(
                file=audio,
                message=track_info,
                attributes=[
                    types.DocumentAttributeAudio(
                        duration=now["track"]["duration"],
                        title=now["track"]["title"],
                        performer=", ".join(now["track"]["artist"])
                    )
                ],
                parse_mode='html'
            )
        except Exception as e:
            logger.error(f"Ошибка ym: {str(e)}", exc_info=True)
            await msg.edit("<b>❌ Ошибка при получении трека</b>", parse_mode='html')

    handlers.append(ym_handler)

    # Команда .ymb - Получить текущий трек (баннер)
    @client.on(events.NewMessage(pattern=f'^{prefix}ymb$', outgoing=True))
    async def ymb_handler(event):
        if not YM_CLIENT:
            return await event.edit("<b>❌ Токен не установлен!</b> Используйте <code>.settoken ваш_токен</code>", parse_mode='html')
        
        try:
            msg = await event.edit("<i>⚡ Получаю информацию о треке...</i>", parse_mode='html')
            now = await get_cached_now_playing()
            
            if not now:
                return await msg.edit("<b>❌ Сейчас ничего не играет</b>", parse_mode='html')
            
            track_info = format_track_info(now)
            await msg.edit(track_info + "\n<i>⚡ Создаю баннер...</i>", parse_mode='html')
            
            # Параллельная загрузка изображения и создание баннера
            cover = await asyncio.get_event_loop().run_in_executor(
                executor,
                lambda: requests.get(now["track"]["img"], timeout=10).content
            )
            
            banner = await asyncio.get_event_loop().run_in_executor(
                executor,
                lambda: create_banner(
                    now["track"]["title"],
                    now["track"]["artist"],
                    now["duration_ms"],
                    now["progress_ms"],
                    cover
                )
            )
            
            await msg.delete()
            await event.reply(
                file=banner,
                message=track_info,
                parse_mode='html'
            )
        except Exception as e:
            logger.error(f"Ошибка ymb: {str(e)}", exc_info=True)
            await msg.edit("<b>❌ Ошибка при создании баннера</b>", parse_mode='html')

    handlers.append(ymb_handler)

    # Команда .ylike - Лайкнуть трек
    @client.on(events.NewMessage(pattern=f'^{prefix}ylike$', outgoing=True))
    async def ylike_handler(event):
        if not YM_CLIENT:
            return await event.edit("<b>❌ Токен не установлен!</b> Используйте <code>.settoken ваш_токен</code>", parse_mode='html')
        
        try:
            msg = await event.edit("<i>⚡ Обрабатываю...</i>", parse_mode='html')
            now = await get_cached_now_playing()
            
            if not now:
                return await msg.edit("<b>❌ Сейчас ничего не играет</b>", parse_mode='html')
            
            await asyncio.get_event_loop().run_in_executor(
                executor,
                lambda: YM_CLIENT.users_likes_tracks_add(now["track"]["track_id"])
            )
            
            await msg.edit(f"<b>❤️ Трек</b> <code>{now['track']['title']}</code> <b>лайкнут!</b>", parse_mode='html')
        except Exception as e:
            logger.error(f"Ошибка ylike: {str(e)}", exc_info=True)
            await msg.edit("<b>❌ Ошибка при лайке трека</b>", parse_mode='html')

    handlers.append(ylike_handler)

    # Команда .ydislike - Дизлайкнуть трек
    @client.on(events.NewMessage(pattern=f'^{prefix}ydislike$', outgoing=True))
    async def ydislike_handler(event):
        if not YM_CLIENT:
            return await event.edit("<b>❌ Токен не установлен!</b> Используйте <code>.settoken ваш_токен</code>", parse_mode='html')
        
        try:
            msg = await event.edit("<i>⚡ Обрабатываю...</i>", parse_mode='html')
            now = await get_cached_now_playing()
            
            if not now:
                return await msg.edit("<b>❌ Сейчас ничего не играет</b>", parse_mode='html')
            
            await asyncio.get_event_loop().run_in_executor(
                executor,
                lambda: YM_CLIENT.users_dislikes_tracks_add(now["track"]["track_id"])
            )
            
            await msg.edit(f"<b>💔 Трек</b> <code>{now['track']['title']}</code> <b>дизлайкнут!</b>", parse_mode='html')
        except Exception as e:
            logger.error(f"Ошибка ydislike: {str(e)}", exc_info=True)
            await msg.edit("<b>❌ Ошибка при дизлайке трека</b>", parse_mode='html')

    handlers.append(ydislike_handler)

    # Команда .settoken - Установить токен
    @client.on(events.NewMessage(pattern=f'^{prefix}settoken(?:\s+(.*))?$', outgoing=True))
    async def settoken_handler(event):
        global YM_TOKEN, YM_CLIENT
        token = event.pattern_match.group(1)
        
        if not token:
            return await event.edit("<b>❌ Укажите токен:</b> <code>.settoken ваш_токен</code>", parse_mode='html')
        
        try:
            YM_CLIENT = await asyncio.get_event_loop().run_in_executor(
                executor,
                lambda: yandex_music.Client(token).init()
            )
            YM_TOKEN = token
            CACHE.clear()
            await event.edit("<b>✅ Токен успешно установлен!</b>", parse_mode='html')
        except Exception as e:
            logger.error(f"Ошибка settoken: {str(e)}", exc_info=True)
            await event.edit("<b>❌ Неверный токен или ошибка подключения</b>", parse_mode='html')

    handlers.append(settoken_handler)

    return handlers

async def get_now_playing(token, client):
    """Получить текущий играющий трек"""
    if not token or not client:
        return None

    try:
        device_id = ''.join(random.choices(string.ascii_lowercase, k=16))
        ws_proto = {
            "Ynison-Device-Id": device_id,
            "Ynison-Device-Info": json.dumps({"app_name": "Chrome", "type": 1}),
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                "wss://ynison.music.yandex.ru/redirector.YnisonRedirectService/GetRedirectToYnison",
                headers={
                    "Sec-WebSocket-Protocol": f"Bearer, v2, {json.dumps(ws_proto)}",
                    "Origin": "http://music.yandex.ru",
                    "Authorization": f"OAuth {token}",
                },
                timeout=10
            ) as ws:
                response = await ws.receive()
                data = json.loads(response.data)
                
            ws_proto["Ynison-Redirect-Ticket"] = data["redirect_ticket"]
            
            payload = {
                "update_full_state": {
                    "player_state": {
                        "player_queue": {
                            "current_playable_index": -1,
                            "entity_id": "",
                            "entity_type": "VARIOUS",
                            "playable_list": [],
                            "options": {"repeat_mode": "NONE"},
                            "entity_context": "BASED_ON_ENTITY_BY_DEFAULT",
                            "version": {"device_id": device_id, "version": 9021243204784341000, "timestamp_ms": 0},
                            "from_optional": "",
                        },
                        "status": {
                            "duration_ms": 0,
                            "paused": True,
                            "playback_speed": 1,
                            "progress_ms": 0,
                            "version": {"device_id": device_id, "version": 8321822175199937000, "timestamp_ms": 0},
                        },
                    },
                    "device": {
                        "capabilities": {"can_be_player": True, "can_be_remote_controller": False, "volume_granularity": 16},
                        "info": {
                            "device_id": device_id,
                            "type": "WEB",
                            "title": "Chrome Browser",
                            "app_name": "Chrome",
                        },
                        "volume_info": {"volume": 0},
                        "is_shadow": True,
                    },
                    "is_currently_active": False,
                },
                "rid": "ac281c26-a047-4419-ad00-e4fbfda1cba3",
                "player_action_timestamp_ms": 0,
                "activity_interception_type": "DO_NOT_INTERCEPT_BY_DEFAULT",
            }
            
            async with session.ws_connect(
                f"wss://{data['host']}/ynison_state.YnisonStateService/PutYnisonState",
                headers={
                    "Sec-WebSocket-Protocol": f"Bearer, v2, {json.dumps(ws_proto)}",
                    "Origin": "http://music.yandex.ru",
                    "Authorization": f"OAuth {token}",
                },
                timeout=10
            ) as ws:
                await ws.send_str(json.dumps(payload))
                response = await ws.receive()
                ynison = json.loads(response.data)
        
        if not ynison.get("player_state", {}).get("player_queue", {}).get("playable_list", []):
            return None
            
        raw_track = ynison["player_state"]["player_queue"]["playable_list"][
            ynison["player_state"]["player_queue"]["current_playable_index"]
        ]
        
        if raw_track["playable_type"] == "LOCAL_TRACK":
            return None
            
        track = await asyncio.get_event_loop().run_in_executor(
            executor,
            lambda: client.tracks(raw_track["playable_id"])[0]
        )
        
        return {
            "paused": ynison["player_state"]["status"]["paused"],
            "duration_ms": int(ynison["player_state"]["status"]["duration_ms"]),
            "progress_ms": int(ynison["player_state"]["status"]["progress_ms"]),
            "track": {
                "track_id": track.track_id.split(":")[0],
                "album_id": track.albums[0].id,
                "title": track.title,
                "artist": track.artists_name(),
                "img": f"https://{track.cover_uri[:-2]}1000x1000",
                "duration": track.duration_ms // 1000,
                "download_link": track.get_download_info(get_direct_links=True)[0].direct_link
            }
        }
    except Exception as e:
        logger.error(f"Ошибка get_now_playing: {str(e)}", exc_info=True)
        return None

def format_track_info(now):
    return (
        f"🎧 <b>{', '.join(now['track']['artist'])} — {now['track']['title']}</b>\n\n"
        f"⏳ <b>Длительность:</b> {now['track']['duration'] // 60}:{now['track']['duration'] % 60:02}\n"
        f"🔗 <a href=\"https://music.yandex.ru/album/{now['track']['album_id']}/track/{now['track']['track_id']}\">Ссылка на трек</a>"
    )

def create_banner(title, artists, duration, progress, cover):
    w, h = 1920, 768
    
    try:
        # Загрузка шрифтов с fallback
        try:
            title_font = ImageFont.truetype(io.BytesIO(requests.get(
                "https://raw.githubusercontent.com/kamekuro/assets/master/fonts/Onest-Bold.ttf",
                timeout=5
            ).content), 80)
            art_font = ImageFont.truetype(io.BytesIO(requests.get(
                "https://raw.githubusercontent.com/kamekuro/assets/master/fonts/Onest-Regular.ttf",
                timeout=5
            ).content), 55)
            time_font = ImageFont.truetype(io.BytesIO(requests.get(
                "https://raw.githubusercontent.com/kamekuro/assets/master/fonts/Onest-Bold.ttf",
                timeout=5
            ).content), 36)
        except:
            title_font = ImageFont.load_default(size=40)
            art_font = ImageFont.load_default(size=30)
            time_font = ImageFont.load_default(size=20)

        # Создание фона
        with Image.open(io.BytesIO(cover)).convert("RGBA") as track_cov:
            banner = track_cov.resize((w, w)).crop((0, (w-h)//2, w, ((w-h)//2)+h))
            banner = banner.filter(ImageFilter.GaussianBlur(radius=14))
            banner = ImageEnhance.Brightness(banner).enhance(0.3)

            # Обложка трека
            track_cov_resized = track_cov.resize((banner.size[1]-150, banner.size[1]-150))
            mask = Image.new("L", track_cov_resized.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle((0, 0, track_cov_resized.size[0], track_cov_resized.size[1]), radius=35, fill=255)
            track_cov_resized.putalpha(mask)
            track_cov_resized = track_cov_resized.crop(track_cov_resized.getbbox())
            banner.paste(track_cov_resized, (75, 75), track_cov_resized)

        # Текст
        draw = ImageDraw.Draw(banner)
        title_lines = textwrap.wrap(title, 23)[:2]
        artists_lines = textwrap.wrap(" • ".join(artists), width=40)[:2]

        x, y = 150+track_cov_resized.size[0], 110
        for line in title_lines:
            draw.text((x, y), line, font=title_font, fill="#FFFFFF")
            y += 70
        
        x, y = 150+track_cov_resized.size[0], 110*2 + (70 if len(title_lines) > 1 else 0)
        for line in artists_lines:
            draw.text((x, y), line, font=art_font, fill="#A0A0A0")
            y += 50

        # Прогресс-бар
        progress_width = min(int(1072*(progress/duration)), 1072)
        draw.rounded_rectangle([768, 650, 768+1072, 650+15], radius=15//2, fill="#A0A0A0")
        draw.rounded_rectangle([768, 650, 768+progress_width, 650+15], radius=15//2, fill="#FFFFFF")
        
        current_time = f"{(progress//1000//60):02}:{(progress//1000%60):02}"
        total_time = f"{(duration//1000//60):02}:{(duration//1000%60):02}"
        
        draw.text((768, 600), current_time, font=time_font, fill="#FFFFFF")
        draw.text((1745, 600), total_time, font=time_font, fill="#FFFFFF")

        # Сохранение
        by = io.BytesIO()
        banner.save(by, format="PNG", optimize=True, quality=85)
        by.seek(0)
        by.name = "banner.png"
        return by
    except Exception as e:
        logger.error(f"Ошибка create_banner: {str(e)}", exc_info=True)
        raise