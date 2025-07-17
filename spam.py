
"""
Описание: Модуль для спама сообщениями с настройкой задержки
"""
version = "2.2"
commands = {
    "spam <кол-во> <текст/реплай>": "отправить спам"
}    
from telethon import events
import asyncio
import re

class SpamModule:
    def __init__(self):
        self.active_tasks = set()
        self.max_messages = 50  # Лимит сообщений
        self.min_delay = 0.3    # Минимальная задержка (сек)

    async def on_load(self, client, prefix):
        """Инициализация модуля"""
        self.client = client
        self.prefix = prefix
        
        @client.on(events.NewMessage(
            pattern=rf'^{re.escape(prefix)}spam(?:\s+(\d+))?(?:\s+(.+))?$',
            outgoing=True
        ))
        async def spam_handler(event):
            await self._handle_spam(event)

    async def _handle_spam(self, event):
        """Обработчик команды спама"""
        if not await self._is_owner(event):
            return

        try:
            args = event.pattern_match.groups()
            count = min(int(args[0] or 5), self.max_messages)
            
            # Получаем текст для спама
            if event.is_reply:
                replied = await event.get_reply_message()
                text = replied.text or replied.raw_text
            elif args[1]:
                text = args[1]
            else:
                await event.edit(
                    f"ℹ️ Использование:\n"
                    f"`{self.prefix}spam [кол-во=5] [текст]`\n"
                    f"Или ответьте на сообщение"
                )
                return

            await event.delete()
            task = asyncio.create_task(
                self._run_spam(event.chat_id, text, count)
            )
            self.active_tasks.add(task)
            task.add_done_callback(self.active_tasks.discard)

        except ValueError:
            await event.edit("❌ Неверное число сообщений!")
        except Exception as e:
            await event.edit(f"⚠️ Ошибка: {str(e)}")

    async def _run_spam(self, chat_id, text, count):
        """Выполняет спам с защитой от ошибок"""
        try:
            for _ in range(count):
                await self.client.send_message(chat_id, text)
                await asyncio.sleep(self.min_delay)
        except Exception as e:
            print(f"[SpamModule] Ошибка: {e}")

    async def _is_owner(self, event):
        """Проверяет, является ли отправитель владельцем"""
        user = await event.client.get_me()
        return event.sender_id == user.id

# Инициализация модуля
module = SpamModule()

async def on_load(client, prefix):
    """Точка входа для загрузки модуля"""
    await module.on_load(client, prefix)
