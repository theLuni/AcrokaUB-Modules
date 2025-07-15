"""
Продвинутый модуль погоды с интерактивными элементами

Предоставляет актуальную информацию о погоде и прогнозы
с использованием API OpenWeatherMap.
"""

version = "2.0"  # Версия модуля
commands = {      # Список команд с описанием
    "weather": "Получить текущую погоду для указанного города",
    "wset": "Установить город по умолчанию и настройки",
    "forecast": "Получить прогноз погоды на 5 дней"
}

import logging
import requests
import pytz
from datetime import datetime
from telethon import events

logger = logging.getLogger(__name__)

class WeatherDB:
    def __init__(self):
        self.default_city = None
        self.units = 'metric'
        self.lang = 'ru'

weather_db = WeatherDB()

async def on_load(client, prefix):
    handlers = []
    
    @client.on(events.NewMessage(pattern=f'^{prefix}wset(?:\s+(.+))?$'))
    async def set_city_handler(event):
        """Установить город по умолчанию и настройки"""
        args = event.pattern_match.group(1)
        if not args:
            current = weather_db.default_city or "не установлен"
            await event.edit(
                f"🌍 Текущие настройки:\n"
                f"Город: {current}\n"
                f"Единицы: {weather_db.units}\n"
                f"Язык: {weather_db.lang}\n\n"
                f"Используйте: {prefix}wset <город> [metric|imperial] [ru|en]"
            )
            return
            
        parts = args.split()
        weather_db.default_city = parts[0]
        
        if len(parts) > 1:
            weather_db.units = parts[1] if parts[1] in ['metric', 'imperial'] else 'metric'
        if len(parts) > 2:
            weather_db.lang = parts[2] if parts[2] in ['ru', 'en'] else 'ru'
            
        await event.edit(
            f"✅ Настройки обновлены:\n"
            f"Город: {weather_db.default_city}\n"
            f"Единицы: {weather_db.units}\n"
            f"Язык: {weather_db.lang}"
        )
    handlers.append(set_city_handler)
    
    @client.on(events.NewMessage(pattern=f'^{prefix}weather(?:\s+(.+))?$'))
    async def weather_handler(event):
        """Получить текущую погоду"""
        city = event.pattern_match.group(1) or weather_db.default_city
        if not city:
            await event.edit(f"❌ Город не указан. Используйте: {prefix}wset <город>")
            return
            
        try:
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {
                'q': city,
                'appid': '27f55366fdc2d2df4bdcdb6a2295251c',
                'units': weather_db.units,
                'lang': weather_db.lang
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('cod') != 200:
                await event.edit(f"❌ Ошибка: {data.get('message', 'Неизвестная ошибка')}")
                return
                
            timezone = pytz.timezone(pytz.country_timezones[data['sys']['country']][0])
            local_time = datetime.now(timezone).strftime("%H:%M")
            
            weather_text = (
                f"🌤 Погода в {data['name']} ({local_time}):\n"
                f"🌡 Температура: {round(data['main']['temp'])}°C\n"
                f"🎭 Ощущается как: {round(data['main']['feels_like'])}°C\n"
                f"💨 Ветер: {data['wind']['speed']} m/s\n"
                f"💧 Влажность: {data['main']['humidity']}%\n"
                f"☁️ {data['weather'][0]['description'].capitalize()}"
            )
            
            await event.edit(weather_text)
            
        except Exception as e:
            logger.error(f"Weather error: {e}")
            await event.edit("❌ Ошибка при получении данных о погоде")
    handlers.append(weather_handler)
    
    @client.on(events.NewMessage(pattern=f'^{prefix}forecast(?:\s+(.+))?$'))
    async def forecast_handler(event):
        """Прогноз погоды на 5 дней"""
        city = event.pattern_match.group(1) or weather_db.default_city
        if not city:
            await event.edit(f"❌ Город не указан. Используйте: {prefix}wset <город>")
            return
            
        try:
            url = "https://api.openweathermap.org/data/2.5/forecast"
            params = {
                'q': city,
                'appid': '27f55366fdc2d2df4bdcdb6a2295251c',
                'units': weather_db.units,
                'lang': weather_db.lang,
                'cnt': 40
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('cod') != '200':
                await event.edit(f"❌ Ошибка: {data.get('message', 'Неизвестная ошибка')}")
                return
                
            forecast_text = f"📅 Прогноз погоды в {city} на 5 дней:\n\n"
            current_date = None
            
            for item in data['list']:
                date = datetime.fromtimestamp(item['dt']).strftime('%d.%m')
                if date != current_date:
                    current_date = date
                    forecast_text += (
                        f"📌 {date}:\n"
                        f"🌡 {round(item['main']['temp'])}°C | "
                        f"💨 {item['wind']['speed']} m/s | "
                        f"💧 {item['main']['humidity']}% | "
                        f"{item['weather'][0]['description']}\n\n"
                    )
                    
            await event.edit(forecast_text)
            
        except Exception as e:
            logger.error(f"Forecast error: {e}")
            await event.edit("❌ Ошибка при получении прогноза погоды")
    handlers.append(forecast_handler)
    
    return handlers