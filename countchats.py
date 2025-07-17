"""
Расширенный анализ чатов с поиском, статистикой и фильтрацией
"""
version = "3.2"
commands = {
    "countchats": "- начать подсчет чатов"
}    
from telethon import events
import time
from datetime import datetime, timedelta
import pytz

async def on_load(client, prefix):
    handlers = []
    
    class Strings:
        personal_chats = "👤 Личные чаты: {} (📅 {} активных)"
        groups = "👥 Группы: {} (📅 {} активных, 🗄 {} архивных)"
        channels = "📡 Каналы: {} (📅 {} активных)"
        bots = "🤖 Боты: {}"
        total = "📊 Всего чатов: {}"
        time = "⏱ Анализ занял: {:.2f}с"
        calculating = "🔍 Анализирую ваши чаты..."
        no_chats = "❌ Чаты не найдены"
        error = "⚠️ Ошибка: {}"

    # Общая функция для обработки дат
    def process_date(date):
        if not date:
            return datetime.now(pytz.utc)
        if date.tzinfo is None:
            return date.replace(tzinfo=pytz.utc)
        return date.astimezone(pytz.utc)

    @client.on(events.NewMessage(pattern=f'^{prefix}countchats(?: (\\d+))?$', outgoing=True))
    async def countchats_handler(event):
        """Полная статистика чатов с фильтром по активности"""
        try:
            start_time = time.time()
            msg = await event.edit(Strings.calculating)
            
            days_threshold = int(event.pattern_match.group(1)) if event.pattern_match.group(1) else 30
            cutoff_date = datetime.now(pytz.utc) - timedelta(days=days_threshold)
            
            stats = {
                'personal': {'total': 0, 'active': 0},
                'groups': {'total': 0, 'active': 0, 'archived': 0},
                'channels': {'total': 0, 'active': 0},
                'bots': {'total': 0},
                'active': 0,
                'inactive': 0
            }

            async for dialog in client.iter_dialogs():
                last_active = process_date(getattr(dialog, 'date', None))
                is_active = last_active > cutoff_date
                
                if dialog.is_user:
                    stats['personal']['total'] += 1
                    if is_active: stats['personal']['active'] += 1
                elif dialog.is_group:
                    stats['groups']['total'] += 1
                    if is_active: stats['groups']['active'] += 1
                    if dialog.archived: stats['groups']['archived'] += 1
                elif dialog.is_channel:
                    stats['channels']['total'] += 1
                    if is_active: stats['channels']['active'] += 1
                elif getattr(dialog.entity, 'bot', False):
                    stats['bots']['total'] += 1
                
                if is_active:
                    stats['active'] += 1
                else:
                    stats['inactive'] += 1

            total = sum([
                stats['personal']['total'],
                stats['groups']['total'],
                stats['channels']['total'],
                stats['bots']['total']
            ])
            
            if not total:
                return await msg.edit(Strings.no_chats)
            
            elapsed = time.time() - start_time
            
            # Формируем ответ
            response = [
                f"{Strings.personal_chats.format(stats['personal']['total'], stats['personal']['active'])}",
                f"{Strings.groups.format(stats['groups']['total'], stats['groups']['active'], stats['groups']['archived'])}",
                f"{Strings.channels.format(stats['channels']['total'], stats['channels']['active'])}",
                f"{Strings.bots.format(stats['bots']['total'])}",
                f"\n{Strings.total.format(total)}",
                f"\n💬 Активных чатов: {stats['active']}",
                f"💤 Неактивных чатов: {stats['inactive']}",
                f"{Strings.time.format(elapsed)}"
            ]
            
            await msg.edit("\n".join(response))
            
        except Exception as e:
            await event.edit(Strings.error.format(str(e)))

    handlers.append(countchats_handler)
    return handlers
