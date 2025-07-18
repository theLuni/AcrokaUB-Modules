"""
Голосовые сообщения
Преобразование голосовых сообщений в текст и текста в голос
"""
version = "1.3"

commands = {
    "v2t": "голосовое в текст",
    "t2v": "текст в голос"
}
# requires: SpeechRecognition pydub gTTS
# system_requires: ffmpeg flac
from telethon import events
from telethon.tl.types import DocumentAttributeAudio
import speech_recognition as sr
import os
from gtts import gTTS
from pydub import AudioSegment
import tempfile

async def on_load(client, prefix):
    handlers = []
    
    # Голосовое сообщение в текст
    @client.on(events.NewMessage(pattern=f'^{prefix}v2t$', outgoing=True))
    async def voice_to_text_handler(event):
        reply = await event.get_reply_message()
        if not reply or not reply.voice:
            await event.edit("❌ Ответьте на голосовое сообщение!")
            return
            
        await event.edit("🔍 Обрабатываю голосовое сообщение...")
        
        try:
            # Скачиваем голосовое сообщение
            voice_ogg = await reply.download_media()
            
            # Конвертируем ogg в wav
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_wav:
                wav_path = tmp_wav.name
                audio = AudioSegment.from_file(voice_ogg)
                audio.export(wav_path, format="wav")
            
            # Распознаем текст
            r = sr.Recognizer()
            with sr.AudioFile(wav_path) as source:
                audio_data = r.record(source)
                text = r.recognize_google(audio_data, language='ru-RU')
            
            await event.edit(f"📝 Текст из голосового сообщения:\n\n{text}")
            
        except Exception as e:
            await event.edit(f"❌ Ошибка распознавания: {str(e)}")
        finally:
            # Удаляем временные файлы
            if 'voice_ogg' in locals() and os.path.exists(voice_ogg):
                os.remove(voice_ogg)
            if 'wav_path' in locals() and os.path.exists(wav_path):
                os.remove(wav_path)
    
    handlers.append(voice_to_text_handler)
    
    # Текст в голосовое сообщение
    @client.on(events.NewMessage(pattern=f'^{prefix}t2v(?: |$)(.*)', outgoing=True))
    async def text_to_voice_handler(event):
        text = event.pattern_match.group(1)
        if not text:
            await event.edit(f"❌ Укажите текст после команды, например: `{prefix}t2v Привет, как дела?`")
            return
            
        await event.edit("🔊 Преобразую текст в голос...")
        try:
            tts = gTTS(text=text, lang='ru')
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_mp3:
                mp3_path = tmp_mp3.name
                tts.save(mp3_path)
            
                await event.client.send_file(
                    event.chat_id,
                    mp3_path,
                    voice_note=True,
                    attributes=[DocumentAttributeAudio(duration=0, voice=True)],
                    reply_to=event.reply_to_msg_id
                )
            await event.delete()
        except Exception as e:
            await event.edit(f"❌ Ошибка преобразования: {str(e)}")
        finally:
            if 'mp3_path' in locals() and os.path.exists(mp3_path):
                os.remove(mp3_path)
    
    handlers.append(text_to_voice_handler)
    
    return handlers