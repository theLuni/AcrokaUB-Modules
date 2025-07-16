"""
Модуль для запросов к нейросети через API
"""

version = "2.3"

commands = {
    "ai": "задать вопрос нейросети",
    "aimodel": "установить модель"
}
import json
import aiohttp
import base64
from telethon import events

async def on_load(client, prefix):
    handlers = []
    
    # Инициализация параметров модуля
    class ModuleState:
        def __init__(self):
            self.default_model = "gpt-4o-mini"
            self.api_url = "http://109.172.94.236:5001/OnlySq-Zetta/v1/models"
    
    state = ModuleState()

    # Команда .ai
    @client.on(events.NewMessage(pattern=f'^{prefix}ai(?: |$)(.*)', outgoing=True))
    async def ai_handler(event):
        """Отправляет запрос к нейросети. Использование: .ai <запрос>"""
        args = event.pattern_match.group(1).strip()
        if not args:
            await event.edit("❌ Введите запрос после команды.\nПример: `.ai Привет! Как дела?`")
            return

        await event.edit("🤔 Думаю...")
        
        payload = {
            "model": state.default_model,
            "request": {
                "messages": [
                    {"role": "user", "content": args}
                ]
            }
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(state.api_url, json=payload) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    # Улучшенная обработка ответа
                    answer = data.get("answer", "")
                    if not answer:
                        answer = data.get("response", "🚫 Ответ не получен или имеет неожиданный формат")
                    
                    # Попытка декодировать base64 если ответ выглядит закодированным
                    if isinstance(answer, str) and "=" in answer and len(answer) % 4 == 0:
                        try:
                            answer = base64.b64decode(answer).decode('utf-8')
                        except:
                            pass
                    
                    # Ограничение длины сообщения для Telegram
                    if len(answer) > 4000:
                        answer = answer[:4000] + "... [сообщение сокращено]"
                    
                    await event.edit(f"💡 Ответ:\n{answer}")
                    
        except aiohttp.ClientError as e:
            await event.edit(f"⚠️ Ошибка подключения к API: {str(e)}")
        except json.JSONDecodeError:
            await event.edit("⚠️ Ошибка: сервер вернул невалидный JSON")
        except Exception as e:
            await event.edit(f"⚠️ Неожиданная ошибка: {str(e)}")

    handlers.append(ai_handler)

    # Команда .aimodel
    @client.on(events.NewMessage(pattern=f'^{prefix}aimodel(?: |$)(.*)', outgoing=True))
    async def aimodel_handler(event):
        """Устанавливает модель ИИ. Использование: .aimodel <название>"""
        args = event.pattern_match.group(1).strip()
        if not args:
            await event.edit(f"❌ Укажите модель. Текущая модель: {state.default_model}")
            return
        
        state.default_model = args
        await event.edit(f"✅ Модель изменена на: {state.default_model}")

    handlers.append(aimodel_handler)
    
    return handlers
