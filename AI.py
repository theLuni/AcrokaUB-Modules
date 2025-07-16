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

    def decode_possible_base64(text):
        """Пытается декодировать строку из base64 с несколькими попытками"""
        if not isinstance(text, str):
            return text
            
        # Варианты base64 строк (могут иметь разное заполнение)
        for _ in range(3):
            try:
                # Удаляем возможные лишние символы в начале/конце
                clean_text = text.strip()
                # Декодируем и возвращаем если получилось
                decoded = base64.b64decode(clean_text).decode('utf-8')
                if decoded:  # Проверяем что декодирование дало результат
                    return decoded
            except:
                # Если не получилось, пробуем добавить padding
                if len(text) % 4 != 0:
                    text += "=" * (4 - len(text) % 4)
                else:
                    break
        return text

    def clean_response(text):
        """Очистка ответа от артефактов и невидимых символов"""
        if not isinstance(text, str):
            return str(text)
            
        # Удаляем невидимые управляющие символы
        text = re.sub(r'[\u200b-\u200f\u202a-\u202e\ufeff]', '', text)
        # Удаляем лишние переносы строк
        text = re.sub(r'\n{3,}', '\n\n', text)
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
                    answer = ""
                    for field in ["answer", "response", "message", "text"]:
                        if field in data and data[field]:
                            answer = str(data[field])
                            break
                    
                    if not answer:
                        answer = "🚫 Ответ не получен или имеет неожиданный формат"
                    
                    # Пытаемся декодировать base64 в любом случае
                    decoded_answer = decode_possible_base64(answer)
                    if decoded_answer != answer:
                        answer = decoded_answer
                    
                    # Очищаем ответ
                    answer = clean_response(answer)
                    
                    # Форматируем вывод
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
