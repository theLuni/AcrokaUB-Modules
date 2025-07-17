"""
.Ultimate Biz Finder - Детальный поиск бизнесов и офисов с полным логированием
"""
version = "6.6"  # Увеличил версию

commands = {
    "ubiz": "поиск уникального бизнеса",
    "uoffice": "поиск уникального офиса",
    "ucfg": "настройка параметров (delay/log_interval) значение",
    "ustop": "остановить текущий поиск"  # Добавлена новая команда
}

import asyncio
from telethon import events
import datetime
import os
import json

# Настройка логирования
LOG_FILE = "ubiz_log.txt"
CONFIG_DIR = "source/mods"
CONFIG_FILE = os.path.join(CONFIG_DIR, "ubiz_config.json")

# Глобальная переменная для управления поиском
ACTIVE_SEARCH = {
    "running": False,
    "stop_requested": False
}

# Создаем директорию для конфигов, если ее нет
os.makedirs(CONFIG_DIR, exist_ok=True)

async def load_config():
    default_config = {
        "delay": 1,
        "log_interval": 2
    }
    
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4)
        return default_config
    
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        try:
            config = json.load(f)
            # Проверяем и добавляем отсутствующие параметры
            for key in default_config:
                if key not in config:
                    config[key] = default_config[key]
            return config
        except json.JSONDecodeError:
            return default_config

async def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

async def log_to_file(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry)

async def on_load(client, prefix):
    handlers = []
    config = await load_config()
    
    @client.on(events.NewMessage(pattern=f'^{prefix}ucfg (delay|log_interval) (\\d+)$', outgoing=True))
    async def config_handler(event):
        param = event.pattern_match.group(1)
        value = int(event.pattern_match.group(2))
        
        if value <= 0:
            await event.edit(f"❌ Значение должно быть больше 0!")
            return
            
        config[param] = value
        await save_config(config)
        
        await event.edit(
            f"✅ <b>Конфигурация обновлена</b>\n\n"
            f"⚙️ <b>{param}:</b> <code>{value}</code>\n\n"
            f"Текущие настройки:\n"
            f"⏳ <b>delay:</b> <code>{config['delay']}</code>\n"
            f"📝 <b>log_interval:</b> <code>{config['log_interval']}</code>",
            parse_mode='html'
        )
        await log_to_file(f"Изменен параметр {param} на {value}")

    @client.on(events.NewMessage(pattern=f'^{prefix}ustop$', outgoing=True))
    async def stop_handler(event):
        if not ACTIVE_SEARCH["running"]:
            await event.edit("ℹ️ <b>Нет активного поиска для остановки</b>", parse_mode='html')
            return
            
        ACTIVE_SEARCH["stop_requested"] = True
        await event.edit("🛑 <b>Запрос на остановку поиска отправлен...</b>", parse_mode='html')
        await log_to_file("Получен запрос на остановку поиска")

    @client.on(events.NewMessage(pattern=f'^{prefix}ubiz$', outgoing=True))
    async def ubiz_handler(event):
        if ACTIVE_SEARCH["running"]:
            await event.edit("⚠️ <b>Уже выполняется другой поиск!</b>\nИспользуйте <code>ustop</code> для остановки", parse_mode='html')
            return
            
        CONFIG = {
            'target_class': 'Уникальный',
            'bot_username': '@Miner_sBot',
            'command': '/gbiz',
            'delay': config['delay'],
            'log_interval': config['log_interval'],
            'type': 'бизнес'
        }
        await run_search(event, CONFIG)
    
    @client.on(events.NewMessage(pattern=f'^{prefix}uoffice$', outgoing=True))
    async def gofice_handler(event):
        if ACTIVE_SEARCH["running"]:
            await event.edit("⚠️ <b>Уже выполняется другой поиск!</b>\nИспользуйте <code>ustop</code> для остановки", parse_mode='html')
            return
            
        CONFIG = {
            'target_class': 'Уникальный',
            'bot_username': '@Miner_sBot',
            'command': '/goffice',
            'delay': config['delay'],
            'log_interval': config['log_interval'],
            'type': 'офис'
        }
        await run_search(event, CONFIG)
    
    async def run_search(event, CONFIG):
        global ACTIVE_SEARCH
        
        ACTIVE_SEARCH = {
            "running": True,
            "stop_requested": False
        }
        
        init_msg = (
            f"🔄 <b>ИНИЦИАЛИЗАЦИЯ ПОИСКА {CONFIG['type'].upper()}А...</b>\n"
            f"🔎 Целевой класс: <code>{CONFIG['target_class']}</code>\n"
            f"🤖 Работаю с ботом: <code>{CONFIG['bot_username']}</code>\n"
            f"⏱ Задержка: <code>{CONFIG['delay']} сек</code>\n"
            f"📝 Интервал логов: <code>{CONFIG['log_interval']} сек</code>\n"
            "▫️▫️▫️▫️▫️▫️▫️▫️▫️"
        )
        log_msg = await event.edit(init_msg, parse_mode='html')
        await log_to_file(f"Инициализация: {init_msg.replace('<b>', '').replace('</b>', '').replace('<code>', '').replace('</code>', '')}")
        
        class State:
            attempts = 0
            last_log = 0
            found = False
            money_error = False

            async def detailed_log(self, text, force=False):
                current_time = asyncio.get_event_loop().time()
                if force or (current_time - self.last_log >= CONFIG['log_interval']):
                    await log_msg.edit(text, parse_mode='html')
                    self.last_log = current_time
                    clean_text = text.replace('<b>', '').replace('</b>', '').replace('<code>', '').replace('</code>', '').replace('<i>', '').replace('</i>', '')
                    await log_to_file(clean_text)
                    return True
                return False

        state = State()

        async def analyze_response():
            try:
                messages = await client.get_messages(CONFIG['bot_username'], limit=3)
                
                for msg in messages:
                    if msg.out:
                        continue
                        
                    raw_text = msg.text
                    
                    if "слишком много" in raw_text.lower():
                        await state.detailed_log(
                            f"⚠️ <b>ОБНАРУЖЕНО:</b> Переполнение {CONFIG['type']}ов\n"
                            "🔄 Отправляю <code>/bsell_all</code>",
                            force=True
                        )
                        await client.send_message(CONFIG['bot_username'], '/bsell_all')
                        await asyncio.sleep(CONFIG['delay'])
                        return False
                    
                    if "не хватает $" in raw_text.lower() or "недостаточно средств" in raw_text.lower():
                        state.money_error = True
                        try:
                            messages_to_delete = await client.get_messages(CONFIG['bot_username'], limit=3)
                            for msg_to_delete in messages_to_delete:
                                if not msg_to_delete.out:
                                    await msg_to_delete.delete()
                        except Exception as delete_error:
                            await log_to_file(f"Ошибка при удалении сообщений: {str(delete_error)}")
                        
                        await state.detailed_log(
                            f"💸 <b>ОШИБКА:</b> Недостаточно денег для покупки\n"
                            f"🚫 <b>ПОИСК ПРЕКРАЩЕН</b>",
                            force=True
                        )
                        await event.respond(
                            f"💸 <b>ПОИСК ОСТАНОВЛЕН!</b>\n\n"
                            f"❌ Деньги закончились для покупки {CONFIG['type']}а\n"
                            f"🔢 <b>Попыток:</b> {state.attempts}",
                            parse_mode='html'
                        )
                        return True
                        
                    win_phrases = ["⭐️ **Ты выиграл", "⭐️ Ты выиграл"]
                    if not any(phrase in raw_text for phrase in win_phrases):
                        continue
                        
                    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
                    if len(lines) < 3:
                        continue
                        
                    item_info = {}
                    for line in lines:
                        if CONFIG['type'] == 'бизнес':
                            if "Бизнес:" in line:
                                item_info['name'] = line.split("Бизнес:")[1].replace("**", "").strip()
                            elif "Класс бизнеса:" in line:
                                item_info['class'] = line.split("Класс бизнеса:")[1].replace("**", "").strip()
                        else:
                            if "Офис:" in line:
                                item_info['name'] = line.split("Офис:")[1].replace("**", "").strip()
                            elif "Класс офиса:" in line:
                                item_info['class'] = line.split("Класс офиса:")[1].replace("**", "").strip()
                    
                    if not item_info.get('name') or not item_info.get('class'):
                        continue
                        
                    state.attempts += 1
                    await state.detailed_log(
                        f"🔎 <b>ПОПЫТКА #{state.attempts}</b>\n"
                        f"🏷️ <b>Название:</b> <code>{item_info['name']}</code>\n"
                        f"🏆 <b>Класс:</b> <code>{item_info['class']}</code>\n"
                        f"🎯 <b>Цель:</b> <code>{CONFIG['target_class']}</code>\n"
                        "▫️▫️▫️▫️▫️▫️▫️▫️▫️"
                    )
                    
                    if item_info['class'].lower() == CONFIG['target_class'].lower():
                        state.found = True
                        await state.detailed_log(
                            f"🎉 <b>УСПЕХ!</b>\n"
                            f"✅ Найден {CONFIG['type']} класса <code>{CONFIG['target_class']}</code>\n"
                            f"🏢 <b>Название:</b> <code>{item_info['name']}</code>\n"
                            f"🔄 <i>Завершаю работу...</i>",
                            force=True
                        )
                        await event.respond(
                            f"✅ <b>ЦЕЛЬ ДОСТИГНУТА!</b>\n\n"
                            f"🏆 <b>Класс:</b> {item_info['class']}\n"
                            f"🏢 <b>{CONFIG['type'].capitalize()}:</b> {item_info['name']}\n"
                            f"🔢 <b>Попыток:</b> {state.attempts}",
                            parse_mode='html'
                        )
                        return True
                        
            except Exception as e:
                error_msg = f"❌ <b>КРИТИЧЕСКАЯ ОШИБКА:</b>\n<code>{str(e)}</code>"
                await state.detailed_log(error_msg, force=True)
                await log_to_file(f"Ошибка: {str(e)}")
                raise
                
            return False

        try:
            while not state.found and not state.money_error and not ACTIVE_SEARCH["stop_requested"]:
                send_msg = f"🔄 <b>ПОПЫТОК:</b> <code>{state.attempts}</code>"
                await state.detailed_log(send_msg, force=True)

                await client.send_message(CONFIG['bot_username'], CONFIG['command'])
                await asyncio.sleep(CONFIG['log_interval'])

                if await analyze_response():
                    break
                    
                state.attempts += 1
                await asyncio.sleep(CONFIG['delay'])
                
            if ACTIVE_SEARCH["stop_requested"]:
                await state.detailed_log(
                    "🛑 <b>ПОИСК ОСТАНОВЛЕН ПОЛЬЗОВАТЕЛЕМ</b>\n\n"
                    f"🔢 <b>Попыток:</b> {state.attempts}",
                    force=True
                )
                await event.respond(
                    f"🛑 <b>ПОИСК ОСТАНОВЛЕН!</b>\n\n"
                    f"🔢 <b>Попыток:</b> {state.attempts}",
                    parse_mode='html'
                )
                
        except Exception as e:
            error_msg = f"🚨 <b>РАБОТА ПРЕРВАНА:</b>\n<code>{str(e)}</code>"
            await state.detailed_log(error_msg, force=True)
            await log_to_file(f"Работа прервана: {str(e)}")
            raise
            
        finally:
            ACTIVE_SEARCH["running"] = False
            ACTIVE_SEARCH["stop_requested"] = False
    
    handlers.extend([ubiz_handler, gofice_handler, config_handler, stop_handler])
    return handlers
