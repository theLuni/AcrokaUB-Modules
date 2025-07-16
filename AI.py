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
import re
from telethon import events

async def on_load(client, prefix):
    handlers = []
    
    class ModuleState:
        def __init__(self):
            self.default_model = "gpt-4o-mini"
            self.api_url = "http://109.172.94.236:5001/OnlySq-Zetta/v1/models"
    
    state = ModuleState()

    def clean_response(text):
        """Очистка ответа от лишних символов и декодирование"""
        # Попытка декодировать base64 если строка выглядит закодированной
        if isinstance(text, str):
            # Проверка на base64 (примерный паттерн)
            base64_pattern = r"^[A-Za-z0-9+/]+={0,2}$"
            if re.fullmatch(base64_pattern, text):
                try:
                    decoded = base64.b64decode(text).decode('utf-8')
                    return decoded
                except:
                    pass
            
            # Удаление невидимых Unicode-символов
            text = re.sub(r'[\u200b-\u200f\u202a-\u202e]', '', text)
            
        return text.strip()

    @client.on(events.NewMessage(pattern=f'^{prefix}ai(?: |$)(.*)', outgoing=True))
    async def ai_handler(event):
        """Отправляет запрос к нейросети"""
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
                    
                    # Получаем ответ из разных возможных полей
                    answer = data.get("answer") or data.get("response") or data.get("message") or ""
                    
                    # Очищаем ответ
                    answer = clean_response(answer)
                    
                    if not answer:
                        answer = "🚫 Ответ не получен или имеет неожиданный формат"
                    
                    # Ограничение длины и форматирование
                    if len(answer) > 4000:
                        answer = answer[:3900] + "\n... [сообщение сокращено]"
                    
                    await event.edit(f"💡 Ответ:\n\n{answer}")
                    
        except aiohttp.ClientError as e:
            await event.edit(f"⚠️ Ошибка подключения: {str(e)}")
        except json.JSONDecodeError:
            await event.edit("⚠️ Сервер вернул невалидный JSON")
        except Exception as e:
            await event.edit(f"⚠️ Ошибка: {str(e)}")

    handlers.append(ai_handler)

    @client.on(events.NewMessage(pattern=f'^{prefix}aimodel(?: |$)(.*)', outgoing=True))
    async def aimodel_handler(event):
        """Устанавливает модель ИИ"""
        args = event.pattern_match.group(1).strip()
        if not args:
            await event.edit(f"❌ Укажите модель. Текущая модель: {state.default_model}")
            return
        
        state.default_model = args
        await event.edit(f"✅ Модель изменена на: {state.default_model}")

    handlers.append(aimodel_handler)
    
    return handlers
