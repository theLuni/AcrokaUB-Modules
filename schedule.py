"""
Точное выполнение отложенных сообщений без лишних данных
"""
version = "4.2"
commands = {
    "sch <кол-во> <период> <текст> - запланировать сообщения"
}    
from telethon import events
from datetime import datetime, timedelta
import re
import asyncio

class PureScheduler:
    def __init__(self):
        self.max_messages = 100
        self.max_minutes = 43200
        self.min_minutes = 1

    async def on_load(self, client, prefix):
        self.client = client
        self.prefix = prefix
        
        @client.on(events.NewMessage(
            pattern=f'^{re.escape(prefix)}sch(?:\\s+(\\d+))(?:\\s+(\\d+))(?:\\s+(.+))?$',
            outgoing=True
        ))
        async def scheduler_handler(event):
            await self.handle_schedule_command(event)

    async def handle_schedule_command(self, event):
        if not await self.is_owner(event):
            return

        try:
            args = event.pattern_match.groups()
            count = min(int(args[0]), self.max_messages)
            minutes = min(int(args[1]), self.max_minutes)
            text = args[2] if args[2] else None

            if event.is_reply and not text:
                replied = await event.get_reply_message()
                text = replied.text
            elif not text:
                await event.delete()
                return

            await event.delete()

            first_msg_time = datetime.now() + timedelta(minutes=minutes)
            
            for i in range(count):
                schedule_time = first_msg_time + timedelta(minutes=minutes*i)
                await self.client.send_message(
                    entity=event.chat_id,
                    message=text,
                    schedule=schedule_time
                )

            # Исправленное подтверждение
            await self.client.send_message(
                'me',
                f"✅ Успешно запланировано {count} сообщений\n"
                f"⌛ Первое будет отправлено в {first_msg_time.strftime('%d.%m.%Y %H:%M')}"
            )

        except Exception as e:
            print(f"[Ошибка планировщика]: {str(e)}")

    async def is_owner(self, event):
        me = await event.client.get_me()
        return event.sender_id == me.id

module = PureScheduler()

async def on_load(client, prefix):
    await module.on_load(client, prefix)