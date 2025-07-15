"""
Автоматически выполняет задания в @Miner_sBot
Поддерживает все типы заданий (краш, монетка, колесо, стаканчик, кубик, работа)
"""
version = "4.0"  # Версия модуля
commands = {      # Список команд с описанием
    "bp": "запустить автоматческое выполнение"
}

import re
import asyncio
from telethon import events, types
import logging

class AutoBPController:
    def __init__(self, client, prefix):
        self.client = client
        self.prefix = prefix
        self.bot_username = 'Miner_sBot'
        self.reset_state()
        self.logger = self._setup_logger()
        self.logger.info(f"AutoBP инициализирован (команда: {self.prefix}bp)")

    def _setup_logger(self):
        logger = logging.getLogger('AutoBP')
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)
        return logger

    def reset_state(self):
        """Сброс состояния модуля"""
        self.active = False
        self.current_chat = None
        self.last_message_id = None
        self.initial_delay = 3  # Задержка после первой команды /bp
        self.command_delay = 6  # Задержка между командами
        self.task_count = 0
        self.current_task = None
        self.need_click = False
        self.is_working = False
        self.current_iteration = 0
        self.max_retries = 3
        self.retry_count = 0
        self.is_finalizing = False  # Флаг завершения заданий

    async def initialize(self):
        """Регистрация обработчиков команд"""
        try:
            self.client.add_event_handler(
                self._handle_start_command,
                events.NewMessage(pattern=rf'^{re.escape(self.prefix)}bp$', outgoing=True)
            )
            
            self.client.add_event_handler(
                self._handle_bot_response,
                events.NewMessage(incoming=True, from_users=[self.bot_username])
            )
            
            # Исправленный обработчик callback
            self.client.add_event_handler(
                self._handle_callback,
                events.CallbackQuery(data=re.compile(r'.*'))  # Обрабатываем все callback
            )
            
            self.logger.info("Обработчики команд успешно зарегистрированы")
        except Exception as e:
            self.logger.error(f"Ошибка при регистрации обработчиков: {e}")

    async def _handle_start_command(self, event):
        """Обработка команды запуска"""
        if self.is_working:
            self.logger.warning("Попытка запуска, когда модуль уже работает")
            return
            
        try:
            await event.delete()
            self.active = True
            self.current_chat = event.chat_id
            self.is_working = True
            self.current_iteration = 0
            self.retry_count = 0
            self.is_finalizing = False
            
            self.logger.info(f"Запуск AutoBP в чате {self.current_chat}")
            await self._send_command("/bp")
            await asyncio.sleep(self.initial_delay)  # Добавляем начальную задержку
        except Exception as e:
            self.logger.error(f"Ошибка при запуске: {e}")
            self.reset_state()

    async def _handle_bot_response(self, event):
        """Обработка ответов бота"""
        if not self.is_working or event.chat_id != self.current_chat:
            return

        try:
            message = event.message.text
            self.last_message_id = event.id
            
            # Обновляем последнее сообщение для кнопок
            if event.reply_markup:
                self.last_message_id = event.id

            # Если мы в процессе завершения, просто нажимаем кнопку награды
            if self.is_finalizing:
                if any(phrase in message for phrase in ["отлично! Теперь выберите", "выберите награду", "нажмите кнопку"]):
                    self.logger.info("Найдены кнопки награды, нажимаем...")
                    await self._click_final_button(event)
                    await asyncio.sleep(2)
                    self.reset_state()
                return

            tasks = {
                r"Сыграйте (\d+) игр в краш": ("!краш 1", True),
                r"Сыграйте (\d+) игр в монетку": ("!монетка решка 1", False),
                r"Сыграйте (\d+) игр в колесо": ("!колесо 1", True),
                r"Сходите на работу (\d+) раз": ("/work_1", False),
                r"Сыграйте (\d+) игр в стаканчик": ("!стаканчик 1", True),
                r"Сыграйте (\d+) игр в кубик": ("!кубик 1", False),
                r"Сделайте ставки в казино (\d+) раз": ("!казино 100", True),
                r"Сыграйте (\d+) игр в рулетку": ("!рулетка 1", True)
            }

            for pattern, (cmd, click) in tasks.items():
                if match := re.search(pattern, message):
                    self.task_count = int(match.group(1))
                    self.current_task = cmd
                    self.need_click = click
                    self.current_iteration = 0
                    self.retry_count = 0
                    
                    self.logger.info(f"Найдено задание: {pattern}. Количество: {self.task_count}")
                    await self._execute_tasks()
                    return

            # Обработка сообщения о завершении заданий
            if any(phrase in message for phrase in ["отлично! Теперь выберите", "выберите награду", "нажмите кнопку"]):
                self.logger.info("Обнаружены кнопки выбора награды")
                self.is_finalizing = True
                await self._click_final_button(event)
                await asyncio.sleep(2)
                self.reset_state()

        except Exception as e:
            self.logger.error(f"Ошибка обработки сообщения бота: {e}")
            await self._handle_error()

    async def _handle_callback(self, event):
        """Обработка callback-запросов (нажатий на кнопки)"""
        if not self.is_working or event.chat_id != self.current_chat:
            return
            
        try:
            # Обновляем ID последнего сообщения при нажатии кнопки
            if hasattr(event, 'message') and event.message:
                self.last_message_id = event.message.id
                self.logger.debug(f"Callback получен, обновлен last_message_id: {self.last_message_id}")
        except Exception as e:
            self.logger.error(f"Ошибка обработки callback: {e}")

    async def _execute_tasks(self):
        """Выполнение цепочки заданий"""
        while self.current_iteration < self.task_count and self.is_working:
            try:
                self.current_iteration += 1
                self.logger.info(f"Выполнение задания {self.current_iteration}/{self.task_count}: {self.current_task}")
                
                await self._send_command(self.current_task)
                await asyncio.sleep(self.command_delay)
                
                if self.need_click:
                    if not await self._click_button():
                        self.logger.warning("Не удалось нажать кнопку, повторная попытка...")
                        await asyncio.sleep(2)
                        if not await self._click_button():
                            raise Exception("Не удалось нажать кнопку после повторной попытки")
                    
                    await asyncio.sleep(self.command_delay)
                    
            except Exception as e:
                self.retry_count += 1
                self.logger.error(f"Ошибка выполнения задания ({self.retry_count}/{self.max_retries}): {e}")
                
                if self.retry_count >= self.max_retries:
                    self.logger.error("Достигнуто максимальное количество попыток, сброс...")
                    await self._handle_error()
                    return
                
                await asyncio.sleep(5)
                continue
                
            self.retry_count = 0  # Сброс счетчика при успешном выполнении

        # После выполнения всех заданий
        if self.is_working:
            self.is_finalizing = True
            await self._send_command("/bp")
            await asyncio.sleep(self.command_delay)

    async def _click_final_button(self, event):
        """Нажатие на финальную кнопку выбора награды"""
        try:
            if event.reply_markup:
                self.last_message_id = event.id
                self.logger.info("Попытка нажать финальную кнопку")
                
                # Даем боту время для обработки
                await asyncio.sleep(1)
                
                if not await self._click_button():
                    self.logger.warning("Не удалось нажать финальную кнопку, повторная попытка...")
                    await asyncio.sleep(2)
                    await self._click_button()
        except Exception as e:
            self.logger.error(f"Ошибка при нажатии финальной кнопки: {e}")
            await self._handle_error()

    async def _click_button(self):
        """Нажатие на инлайн-кнопку"""
        if not self.last_message_id or not self.current_chat:
            return False

        try:
            msg = await self.client.get_messages(self.current_chat, ids=self.last_message_id)
            if msg and msg.reply_markup:
                buttons = msg.reply_markup.rows
                if buttons and buttons[0].buttons:
                    # Нажимаем первую кнопку в первом ряду
                    await msg.click(0, 0)
                    self.logger.debug("Успешно нажата кнопка")
                    return True
        except Exception as e:
            self.logger.error(f"Ошибка при нажатии кнопки: {e}")
            
        return False

    async def _send_command(self, command: str):
        """Отправка команды боту"""
        try:
            msg = await self.client.send_message(self.current_chat, command)
            self.last_message_id = msg.id
            self.logger.debug(f"Отправлена команда: {command}")
            return msg
        except Exception as e:
            self.logger.error(f"Ошибка отправки команды {command}: {e}")
            raise

    async def _handle_error(self):
        """Обработка ошибок"""
        try:
            self.logger.warning("Обработка ошибки, попытка восстановления...")
            await asyncio.sleep(5)
            await self._send_command("/bp")
            await asyncio.sleep(self.command_delay)
        except Exception as e:
            self.logger.error(f"Критическая ошибка: {e}")
        finally:
            self.reset_state()

async def on_load(client, prefix):
    """Точка входа для системы модулей"""
    try:
        controller = AutoBPController(client, prefix)
        await controller.initialize()
        return []
    except Exception as e:
        logging.error(f"Ошибка при загрузке модуля AutoBP: {e}")
        return []