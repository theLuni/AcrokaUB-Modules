"""
AI Ассистент на основе DeepSeek AI
"""
version = "1.1"
commands = {
    "luni": "задать вопрос нейросети"
}

import requests
import logging
import time
import os
from telethon import events
from datetime import datetime
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def on_load(client, prefix):
    handlers = []
    
    class LuniAI:
        def __init__(self, client):
            self.client = client
            self.api_url = "https://openrouter.ai/api/v1/chat/completions"
            # Используем переменную окружения для API ключа
            self.api_key = os.getenv("OPENROUTER_API_KEY") or "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"
            self.model = "deepseek/deepseek-r1"
            self.headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://your-site.com",  # Required by OpenRouter
                "X-Title": "LuniAI"  # Required by OpenRouter
            }
            self.timeout = 30

        async def _update_status(self, message, text):
            """Обновление статуса выполнения"""
            try:
                timestamp = datetime.now().strftime("%H:%M:%S")
                await message.edit(f"⏳ {text}\n🕒 {timestamp}")
            except Exception as error:
                logger.error(f"Ошибка обновления статуса: {str(error)}")

        async def _send_request(self, prompt):
            """Отправка запроса к API"""
            try:
                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7,
                        "max_tokens": 2000
                    },
                    timeout=self.timeout
                )
                
                # Улучшенная обработка ошибок
                if response.status_code == 401:
                    logger.error("Ошибка авторизации: неверный или отсутствующий API ключ")
                    return None
                elif response.status_code == 429:
                    logger.error("Превышен лимит запросов")
                    return None
                
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
                
            except requests.exceptions.HTTPError as error:
                logger.error(f"HTTP ошибка: {str(error)}")
                return None
            except requests.exceptions.RequestException as error:
                logger.error(f"Ошибка соединения: {str(error)}")
                return None
            except Exception as error:
                logger.error(f"Неожиданная ошибка: {str(error)}")
                return None

    luni = LuniAI(client)

    @client.on(events.NewMessage(pattern='^' + re.escape(prefix) + 'luni(?:\s+|$)(.*)', outgoing=True))
    async def luni_handler(event):
        """Обработчик команды .luni"""
        try:
            query = event.pattern_match.group(1).strip()
            if not query:
                await event.edit(f"ℹ️ Использование: {prefix}luni <ваш вопрос>")
                return
                
            msg = await event.edit("🧠 Обработка запроса...")
            
            start_time = time.time()
            response = await luni._send_request(query)
            
            if response is None:
                await msg.edit("❌ Ошибка при обращении к нейросети. Проверьте API ключ или попробуйте позже.")
                return
                
            processing_time = int(time.time() - start_time)
            await msg.edit(
                f"💡 Ответ ({processing_time} сек):\n\n"
                f"{response[:4000]}"
            )
            
        except Exception as error:
            logger.error(f"Ошибка в luni_handler: {str(error)}")
            await event.reply(f"⚠️ Ошибка: {str(error)}")

    handlers.append(luni_handler)
    return handlers
