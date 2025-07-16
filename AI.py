"""
Название: AI Module
Описание: Улучшенный модуль для работы с нейросетями
Команды: ai, aimodel, aichat, aicreate, aisup, airw, aipic, aivoice
Версия: 2.5
"""

import json
import aiohttp
import base64
import re
import os
import io
from telethon import events
from PIL import Image
import asyncio

async def on_load(client, prefix):
    handlers = []
    
    class ModuleState:
        def __init__(self):
            self.default_model = "gpt-4"
            self.api_url = "http://109.172.94.236:5001/OnlySq-Zetta/v1/models"
            self.image_api_url = "http://109.172.94.236:5002/OnlySq-Zetta/v1/images"
            self.available_models = {
                "1": "o3-PRO",
                "2": "o1-PRO",
                "3": "o3-Mini-High",
                "4": "Grok 3",
                "5": "GPT 4.1",
                "6": "qwen3-235b-a22b",
                "7": "qwen-max-latest",
                "8": "qwen-plus-2025-01-25",
                "9": "qwen-turbo-2025-02-11",
                "10": "qwen2.5-coder-32b-instruct",
                "11": "qwen2.5-72b-instruct",
                "12": "gpt-4.5",
                "13": "gpt-4o",
                "14": "gpt-4o-mini",
                "15": "gpt4-turbo",
                "16": "gpt-3.5-turbo",
                "17": "gpt-4",
                "18": "deepseek-v3",
                "19": "deepseek-r1",
                "20": "gemini-1.5 Pro",
                "21": "gemini-2.5-pro-exp-03-25",
                "22": "gemini-2.5-flash",
                "23": "gemini-2.0-flash",
                "24": "llama-4-maverick",
                "25": "llama-4-scout",
                "26": "llama-3.3-70b",
                "27": "llama-3.3-8b",
                "28": "llama-3.1",
                "29": "llama-2",
                "30": "claude-3.5-sonnet",
                "31": "claude-3-haiku",
                "32": "bard",
                "33": "qwen",
                "34": "t-pro",
                "35": "t-lite"
            }
    
    state = ModuleState()

    def clean_response(text):
        """Очистка ответа от артефактов"""
        if not isinstance(text, str):
            return str(text)
            
        text = re.sub(r'[\u200b-\u200f\u202a-\u202e\ufeff]', '', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    @client.on(events.NewMessage(pattern=f'^{prefix}ai(?: |$)(.*)', outgoing=True))
    async def ai_handler(event):
        """Задать вопрос ИИ"""
        args = event.pattern_match.group(1).strip()
        if not args:
            await event.edit(f"❌ Введите запрос.\nПример: `{prefix}ai Привет!`")
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
                    answer = data.get("answer", "")
                    
                    if not answer:
                        answer = "🚫 Ответ не получен"
                    
                    answer = clean_response(answer)
                    
                    if len(answer) > 4000:
                        answer = answer[:3900] + "\n... [сообщение сокращено]"
                    
                    await event.edit(f"💡 Ответ ({state.default_model}):\n\n{answer}")
                    
        except Exception as e:
            await event.edit(f"⚠️ Ошибка: {str(e)}")

    @client.on(events.NewMessage(pattern=f'^{prefix}aimodel(?: |$)(.*)', outgoing=True))
    async def aimodel_handler(event):
        """Установить модель ИИ"""
        args = event.pattern_match.group(1).strip()
        
        if not args:
            model_list = "\n".join([f"{k}. {v}" for k, v in state.available_models.items()])
            await event.edit(f"📚 Доступные модели:\n{model_list}\n\nИспользуйте: `{prefix}aimodel <номер>`")
            return
        
        if args in state.available_models:
            state.default_model = state.available_models[args]
            await event.edit(f"✅ Модель изменена на: {state.default_model}")
        else:
            await event.edit("❌ Неверный номер модели. Используйте `.aimodel` для списка.")

    @client.on(events.NewMessage(pattern=f'^{prefix}aipic(?: |$)(.*)', outgoing=True))
    async def aipic_handler(event):
        """Создать изображение по запросу"""
        args = event.pattern_match.group(1).strip()
        if not args:
            await event.edit(f"❌ Введите описание.\nПример: `{prefix}aipic Кот в шляпе`")
            return

        await event.edit("🎨 Создаю изображение...")
        
        payload = {
            "prompt": args,
            "model": "stable-diffusion-xl"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(state.image_api_url, json=payload) as response:
                    response.raise_for_status()
                    data = await response.read()
                    
                    with io.BytesIO(data) as photo:
                        await event.client.send_file(
                            event.chat_id,
                            photo,
                            caption=f"🖼️ Изображение по запросу: {args}",
                            reply_to=event.id
                        )
                    await event.delete()
                    
        except Exception as e:
            await event.edit(f"⚠️ Ошибка генерации: {str(e)}")

    @client.on(events.NewMessage(pattern=f'^{prefix}aivoice(?: |$)(.*)', outgoing=True))
    async def aivoice_handler(event):
        """Озвучить текст"""
        args = event.pattern_match.group(1).strip()
        if not args:
            await event.edit(f"❌ Введите текст.\nПример: `{prefix}aivoice Привет, как дела?`")
            return

        await event.edit("🔊 Озвучиваю текст...")
        
        payload = {
            "text": args,
            "model": "tts-1"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(state.api_url.replace("models", "tts"), json=payload) as response:
                    response.raise_for_status()
                    data = await response.read()
                    
                    with io.BytesIO(data) as voice:
                        await event.client.send_file(
                            event.chat_id,
                            voice,
                            voice_note=True,
                            caption=f"🔊 Озвучка текста: {args[:50]}...",
                            reply_to=event.id
                        )
                    await event.delete()
                    
        except Exception as e:
            await event.edit(f"⚠️ Ошибка озвучки: {str(e)}")

    @client.on(events.NewMessage(pattern=f'^{prefix}aichat(?: |$)', outgoing=True))
    async def aichat_handler(event):
        """Включить режим чата с ИИ"""
        chat = await event.get_chat()
        await event.edit(f"💬 Режим чата с ИИ активирован в этом чате.\nТеперь ИИ будет отвечать на сообщения, начинающиеся с `{prefix}ai`")

    @client.on(events.NewMessage(pattern=f'^{prefix}airw(?: |$)(.*)', outgoing=True))
    async def airw_handler(event):
        """Переписать текст"""
        args = event.pattern_match.group(1).strip()
        reply = await event.get_reply_message()
        
        if not args or not reply:
            await event.edit(f"❌ Ответьте на сообщение и укажите инструкцию.\nПример: `{prefix}airw Сделай короче`")
            return

        await event.edit("✏️ Переписываю текст...")
        
        payload = {
            "model": state.default_model,
            "request": {
                "messages": [
                    {"role": "system", "content": "Перепиши текст по инструкции"},
                    {"role": "user", "content": f"{args}: {reply.text}"}
                ]
            }
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(state.api_url, json=payload) as response:
                    response.raise_for_status()
                    data = await response.json()
                    answer = data.get("answer", "")
                    
                    if not answer:
                        answer = "🚫 Не удалось переписать текст"
                    
                    await event.edit(f"✏️ Переписанный текст:\n\n{answer}")
                    
        except Exception as e:
            await event.edit(f"⚠️ Ошибка: {str(e)}")

    handlers.extend([ai_handler, aimodel_handler, aipic_handler, 
                    aivoice_handler, aichat_handler, airw_handler])
    
    return handlers
