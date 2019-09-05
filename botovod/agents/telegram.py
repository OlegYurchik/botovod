from __future__ import annotations
import aiofiles
import aiohttp
import asyncio
from botovod import utils
from botovod.agents import Agent, Attachment, Chat, Keyboard, KeyboardButton, Location, Message
from datetime import datetime
import json
import logging
import requests
from threading import Thread
from typing import Any, Dict, Iterator, List, Tuple
import time


class TelegramAgent(Agent):
    WEBHOOK = "webhook"
    POLLING = "polling"

    BASE_URL = "https://api.telegram.org/bot{token}/{method}"
    FILE_URL = "https://api.telegram.org/file/bot{token}/{file_path}"

    def __init__(self, token: str, method: str=POLLING, delay: int=5, daemon: bool=False,
                 webhook_url: (str, None)=None, certificate_path: (str, None)=None,
                 logger: logging.Logger=logging.getLogger(__name__)):
        super().__init__(logger)
        self.token = token
        self.method = method

        if method == self.POLLING:
            self.delay = delay
            self.daemon = daemon
            self.thread = None
        elif webhook_url is None:
            raise ValueError("Need set webhook_url")
        else:
            self.webhook_url = webhook_url
            self.certificate_path = certificate_path

        self.last_update = 0

    def start(self):
        self.logger.info("[%s:%s] Starting agent...", self, self.name)

        self.set_webhook()
        self.running = True

        if self.method == self.POLLING:
            if self.thread and self.thread.is_alive():
                self.thread.join()
            self.thread = Thread(target=self.polling, daemon=self.daemon)
            self.thread.start()
            self.logger.info("[%s:%s] Started by polling.", self, self.name)
        elif self.method == self.WEBHOOK:
            self.logger.info("[%s:%s] Started by webhook.", self, self.name)

    async def a_start(self):
        self.logger.info("[%s:%s] Starting agent...", self, self.name)

        await self.a_set_webhook()
        self.running = True

        if self.method == self.POLLING:
            asyncio.create_task(self.a_polling())
            self.logger.info("[%s:%s] Started by polling.", self, self.name)
        elif self.method == self.WEBHOOK:
            self.logger.info("[%s:%s] Started by webhook.", self, self.name)

    def stop(self):
        self.logger.info("[%s:%s] Stopping agent...", self, self.name)

        if self.method == self.POLLING:
            self.thread.join()
            self.thread = None
        self.running = False

        self.logger.info("[%s:%s] Agent stopped.", self, self.name)

    async def a_stop(self):
        self.logger.info("[%s:%s] Stopping agent...", self, self.name)
        self.running = False
        self.logger.info("[%s:%s] Agent stopped.", self, self.name)

    def parser(self, headers: Dict[str, str], body: str) -> List[Tuple[Chat, Message]]:
        update = json.loads(body)
        messages = []
        if update["update_id"] <= self.last_update:
            return messages
        self.last_update = update["update_id"]
        if "message" in update:
            chat = TelegramChat.parse(agent=self, data=update["message"]["chat"])
            message = TelegramMessage.parse(data=update["message"], agent=self)
            messages.append((chat, message))
        if "callback_query" in update:
            data = update["callback_query"]
            if "message" in data:
                chat = TelegramChat.parse(agent=self, data=data["message"]["chat"])
            else:
                chat = TelegramUser.parse(agent=self, data=data["from"])
            message = TelegramCallback.parse(data=update["callback_query"])
            messages.append((chat, message))
        return messages

    async def a_parser(self, headers: Dict[str, str],
                       body: str) -> List[Tuple[Chat, TelegramAgent]]:
        update = json.loads(body)
        messages = []
        if update["update_id"] <= self.last_update:
            return messages
        self.last_update = update["update_id"]
        if "message" in update:
            chat = TelegramChat.parse(agent=self, data=update["message"]["chat"])
            message = await TelegramMessage.a_parse(data=update["message"], agent=self)
            messages.append((chat, message))
        if "callback_query" in update:
            data = update["callback_query"]
            if "message" in data:
                chat = TelegramChat.parse(agent=self, data=data["message"]["chat"])
            else:
                chat = TelegramUser.parse(agent=self, data=data["from"])
            message = TelegramCallback.parse(data=update["callback_query"])
            messages.append((chat, message))
        return messages

    def responser(self, headers: Dict[str, str], body: str) -> Tuple[int, Dict[str, str], str]:
        return 200, {}, ""

    async def a_responser(self, headers: Dict[str, str],
                          body: str) -> Tuple[int, Dict[str, str], str]:
        return self.responser(headers=headers, body=body)

    def polling(self):
        url = self.BASE_URL.format(token=self.token, method="getUpdates")
        while self.running:
            try:
                params = {"offset": self.last_update + 1} if self.last_update > 0 else {}
                response = requests.get(url, params=params)
                updates = response.json()["result"]
                for update in updates:
                    self.listen(response.headers, json.dumps(update))
            except Exception:
                self.logger.exception("[%s:%s] Got exception")
                self.logger.error("[%s:%s] Get incorrect update! Code: %s. Response: %s", self,
                                  self.name, response.status_code, response.text)
            finally:
                time.sleep(self.delay)

    async def a_polling(self):
        url = self.BASE_URL.format(token=self.token, method="getUpdates")
        while self.running:
            try:
                params = {"offset": self.last_update + 1} if self.last_update > 0 else {}
                async with aiohttp.ClientSession() as session:
                    response = await session.get(url, params=params)
                updates = (await response.json())["result"]
                for update in updates:
                    await self.a_listen(dict(response.headers), json.dumps(update))
            except Exception:
                self.logger.exception("[%s:%s] Got exception")
                self.logger.error("[%s:%s] Get incorrect update! Code: %s. Response: %s", self,
                                  self.name, response.status, await response.text())
            finally:
                await asyncio.sleep(self.delay)

    def send_attachment(self, type: str, chat: Chat, attachment: Attachment,
                        keyboard: (Keyboard, None)=None):
        url = self.BASE_URL.format(token=self.token, method="send" + type.capitalize())
        data = {"chat_id": chat.id}
        if "id" in attachment.raw:
            data[type] = attachment.raw["id"]
        elif attachment.url is not None:
            data[type] = attachment.url
            response = requests.post(url, data=data)
        elif attachment.filepath is not None:
            data[type] = open(attachment.filepath)
        else:
            return
        if keyboard is not None:
            if hasattr(keyboard, "render"):
                data["reply_markup"] = keyboard.render()
            else:
                data["reply_markup"] = TelegramKeyboard.default_render(keyboard)
        response = requests.post(url, data=data)
        if response.status_code != 200:
            self.logger.error("[%s:%s] Cannot send photo! Code: %s; Body: %s", self, self.name,
                              response.status_code, response.text)
        else:
            return TelegramMessage.parse(response.json()["result"])

    async def a_send_attachment(self, type: str, chat: Chat, attachment: Attachment,
                                keyboard: (Keyboard, None)=None):
        url = self.BASE_URL.format(token=self.token, method="send" + type.capitalize())
        data = {"chat_id": chat.id}
        if "id" in attachment.raw:
            data[type] = attachment.raw["id"]
        elif attachment.url is not None:
            data[type] = attachment.url
            response = requests.post(url, data=data)
        elif attachment.filepath is not None:
            data[type] = open(attachment.filepath)
        else:
            return
        if keyboard is not None:
            if hasattr(keyboard, "render"):
                data["reply_markup"] = keyboard.render()
            else:
                data["reply_markup"] = TelegramKeyboard.default_render(keyboard)
        async with aiohttp.ClientSession() as session:
            response = await session.post( url, data=data)
        if response.status != 200:
            self.logger.error("[%s:%s] Cannot send photo! Code: %s; Body: %s", self, self.name,
                              response.status, await response.text())
        else:
            return await TelegramMessage.a_parse((await response.json())["result"])

    def set_webhook(self):
        self.logger.info("[%s:%s] Setting webhook...", self, self.name)

        url = self.BASE_URL.format(token=self.token, method="setWebhook")
        if self.method == self.WEBHOOK:
            if self.certificate_path is not None:
                with open(self.certificate_path) as file:
                    response = requests.post(
                        url,
                        data={"url": self.webhook_url},
                        files={"certificate": file},
                    )
            else:
                response = requests.post(url, data={"url": self.webhook_url})
        else:
            response = requests.post(url)
        if response.status_code != 200:
            self.logger.error("[%s:%s] Webhook doesn't set! Code: %s; Body: %s", self, self.name,
                              response.status_code, response.text)
            return

        self.logger.info("[%s:%s] Set webhook.", self, self.name)

    async def a_set_webhook(self):
        self.logger.info("[%s:%s] Setting webhook...", self, self.name)

        url = self.BASE_URL.format(token=self.token, method="setWebhook")
        if self.method == self.WEBHOOK:
            if self.certificate_path is not None:
                async with aiohttp.ClientSession() as session:
                    # async with aiofiles.open(self.certificate_path, mode="rb") as file:
                    with open(self.certificate_path) as file:    
                        response = await session.post(
                            url,
                            data={"url": self.webhook_url, "certificate": file},
                        )
            else:
                async with aiohttp.ClientSession() as session:
                    response = await session.post(url, data={"url": self.webhook_url})
        else:
            async with aiohttp.ClientSession() as session:
                response = await session.post(url)
        if response.status != 200:
            self.logger.error("[%s:%s] Webhook doesn't set! Code: %s; Body: %s", self, self.name,
                              response.status, response.text)
            return

        self.logger.info("[%s:%s] Set webhook.", self, self.name)

    def send_message(self, chat: Chat, text: (str, None)=None, images: Iterator[Attachment]=[],
                     audios: Iterator[Attachment]=[], documents: Iterator[Attachment]=[],
                     videos: Iterator[Attachment]=[], locations: Iterator[Location]=[],
                     keyboard: (Keyboard, None)=None, mode: (str, None)=None,
                     web_preview: bool=True, notification: bool=True,
                     reply: (Message, None)=None):
        messages = []
        if text is not None:
            url = self.BASE_URL.format(token=self.token, method="sendMessage")
            data = {
                "chat_id": chat.id,
                "text": text,
                "disable_web_page_preview": not web_preview,
                "disable_notification": not notification, 
            }
            if keyboard is not None:
                if hasattr(keyboard, "render"):
                    data["reply_markup"] = keyboard.render()
                else:
                    data["reply_markup"] = TelegramKeyboard.default_render(keyboard)
            if mode is not None:
                data["parse_mode"] = mode
            if reply is not None:
                data["reply_to_message_id"] = reply.id
            response = requests.post(url, data=data)
            if response.status_code != 200:
                self.logger.error("[%s:%s] Cannot send message! Code: %s; Body: %s", self,
                                  self.name, response.status_code, response.text)
            else:
                messages.append(TelegramMessage.parse(response.json()["result"]))
        for image in images:
            message = self.send_photo(chat, image, keyboard=keyboard)
            if message is not None:
                messages.append(message)
        for audio in audios:
            message = self.send_audio(chat, audio, keyboard=keyboard)
            if message is not None:
                messages.append(message)
        for document in documents:
            message = self.send_document(chat, document, keyboard=keyboard)
            if message is not None:
                messages.append(message)
        for video in videos:
            message = self.send_video(chat, video, keyboard=keyboard)
            if message is not None:
                messages.append(message)
        for location in locations:
            message = self.send_location(chat, location, keyboard=keyboard)
            if message is not None:
                messages.append(message)
        return messages

    async def a_send_message(self, chat: Chat, text: (str, None)=None,
                             images: Iterator[Attachment]=[], audios: Iterator[Attachment]=[],
                             documents: Iterator[Attachment]=[], videos: Iterator[Attachment]=[],
                             locations: Iterator[Location]=[], keyboard: (Keyboard, None)=None,
                             mode: (str, None)=None, web_preview: bool=True,
                             notification: bool=True, reply: (Message, None)=None):
        messages = []
        if text is not None:
            url = self.BASE_URL.format(token=self.token, method="sendMessage")
            data = {
                "chat_id": chat.id,
                "text": text,
                "disable_web_page_preview": not web_preview,
                "disable_notification": not notification, 
            }
            if keyboard is not None:
                if hasattr(keyboard, "render"):
                    data["reply_markup"] = keyboard.render()
                else:
                    data["reply_markup"] = TelegramKeyboard.default_render(keyboard)
            if mode is not None:
                data["parse_mode"] = mode
            if reply is not None:
                data["reply_to_message_id"] = reply.id
            async with aiohttp.ClientSession() as session:
                response = await session.post(url, data=data)
            if response.status != 200:
                self.logger.error("[%s:%s] Cannot send message! Code: %s; Body: %s", self,
                                  self.name, response.status, await response.text())
            else:
                messages.append(TelegramMessage.parse((await response.json())["result"]))
        for image in images:
            message = await self.a_send_photo(chat, image, keyboard=keyboard)
            if message is not None:
                messages.append(message)
        for audio in  audios:
            message = await self.a_send_audio(chat, audio, keyboard=keyboard)
            if message is not None:
                messages.append(message)
        for document in documents:
            message = await self.a_send_document(chat, document, keyboard=keyboard)
            if message is not None:
                messages.append(message)
        for video in videos:
            message = await self.a_send_video(chat, video, keyboard=keyboard)
            if message is not None:
                messages.append(message)
        for location in locations:
            message = await self.a_send_location(chat, location, keyboard=keyboard)
            if message is not None:
                messages.append(message)
        return messages

    def send_photo(self, chat: Chat, image: Attachment, keyboard: (Keyboard, None)=None):
        return self.send_attachment(type="photo", chat=chat, attachment=image, keyboard=keyboard)

    async def a_send_photo(self, chat: Chat, image: Attachment, keyboard: (Keyboard, None)=None):
        return await self.a_send_attachment(type="photo", chat=chat, attachment=image,
                                            keyboard=keyboard)

    def send_audio(self, chat: Chat, audio: Attachment, keyboard: (Keyboard, None)=None):
        return self.send_attachment(type="audio", chat=chat, attachment=audio, keyboard=keyboard)

    async def a_send_audio(self, chat: Chat, audio: Attachment, keyboard: (Keyboard, None)=None):
        return await self.a_send_attachment(type="audio", chat=chat, attachment=audio,
                                            keyboard=keyboard)

    def send_document(self, chat: Chat, document: Attachment, keyboard: (Keyboard, None)=None):
        return self.send_attachment(type="document", chat=chat, attachment=document,
                                    keyboard=keyboard)

    async def a_send_document(self, chat: Chat, document: Attachment,
                              keyboard: (Keyboard, None)=None):
        return await self.a_send_attachment(type="document", chat=chat, attachment=document,
                                            keyboard=keyboard)

    def send_video(self, chat: Chat, video: Attachment, keyboard: (Keyboard, None)=None):
        return self.send_attachment(type="video", chat=chat, attachment=video, keyboard=keyboard)

    async def a_send_video(self, chat: Chat, video: Attachment, keyboard: (Keyboard, None)=None):
        return await self.a_send_attachment(type="video", chat=chat, attachment=video,
                                            keyboard=keyboard)

    def send_location(self, chat: Chat, location: Location, keyboard: (Keyboard, None)=None):
        url = self.BASE_URL.format(token=self.token, method="sendLocation")
        data = {"chat_id": chat.id, "longitude": location.longitude, "latitude": location.latitude}
        if keyboard is not None:
            if hasattr(keyboard, "render"):
                data["reply_markup"] = keyboard.render()
            else:
                data["reply_markup"] = TelegramKeyboard.default_render(keyboard)
        response = requests.post(url, data=data)
        if response.status_code != 200:
            self.logger.error("[%s:%s] Cannot send location! Code: %s; Body: %s", self, self.name,
                              response.status_code, response.text)
        else:
            return TelegramMessage.parse(response.json())

    async def a_send_location(self, chat: Chat, location: Location,
                              keyboard: (Keyboard, None)=None):
        url = self.BASE_URL.format(token=self.token, method="sendLocation")
        data = {"chat_id": chat.id, "longitude": location.longitude, "latitude": location.latitude}
        if keyboard is not None:
            if hasattr(keyboard, "render"):
                data["reply_markup"] = keyboard.render()
            else:
                data["reply_markup"] = TelegramKeyboard.default_render(keyboard)
        async with aiohttp.ClientSession() as session:
            response = await session.post(url, data=data)
        if response.status != 200:
            self.logger.error("[%s:%s] Cannot send location! Code: %s; Body: %s", self, self.name,
                              response.status, await response.text())
        else:
            return await TelegramMessage.a_parse((await response.json())["result"])

    def get_file(self, file_id: int):
        url = self.BASE_URL.format(token=self.token, method="getFile")
        response = requests.get(url, params={"file_id": file_id})
        if response.status_code != 200:
            self.logger.error("[%s:%s] Cannot get file! Code: %s; Body: %s", self, self.name,
                              response.status_code, response.text)
        return response.json()

    async def a_get_file(self, file_id: int):
        url = self.BASE_URL.format(token=self.token, method="getFile")
        async with aiohttp.ClientSession() as session:
            response = await session.get(url, params={"file_id": file_id})
        if response.status != 200:
            self.logger.error("[%s:%s] Cannot get file! Code: %s; Body: %s", self, self.name,
                              response.status, await response.text())
        return await response.json()

    def edit_message_text(self, chat: Chat, message: TelegramMessage, text: str):
        url = self.BASE_URL.format(token=self.token, method="editMessageText")
        data = {"chat_id": chat.id, "message_id": message.raw["id"], "text": text}
        response = requests.post(url, data=data)
        if response.status_code != 200:
            self.logger.error("[%s:%s] Cannot edit message text! Code: %s; Body: %s", self,
                              self.name, response.status_code, response.text)

    async def a_edit_message_text(self, chat: Chat, message: TelegramMessage, text: str):
        url = self.BASE_URL.format(token=self.token, method="editMessageText")
        data = {"chat_id": chat.id, "message_id": message.raw["id"], "text": text}
        async with aiohttp.ClientSession() as session:
            response = await session.post(url, data=data)
        if response.status != 200:
            self.logger.error("[%s:%s] Cannot edit message text! Code: %s; Body: %s", self,
                              self.name, response.status, await response.text())

    def edit_message_keyboard(self, chat: Chat, message: TelegramMessage,
                              keyboard: TelegramInlineKeyboard):
        url = self.BASE_URL.format(token=self.token, method="editMessageReplyMarkup")
        data = {
            "chat_id": chat.id,
            "message_id": message.raw["id"],
            "reply_markup": keyboard.render(),
        }
        response = requests.post(url, data=data)
        if response.status_code != 200:
            self.logger.error("[%s:%s] Cannot edit message keyboard! Code: %s; Body: %s", self,
                              self.name, response.status_code, response.text)

    async def a_edit_message_keyboard(self, chat: Chat, message: TelegramMessage,
                                      keyboard: TelegramInlineKeyboard):
        url = self.BASE_URL.format(token=self.token, method="editMessageReplyMarkup")
        data = {
            "chat_id": chat.id,
            "message_id": message.raw["id"],
            "reply_markup": keyboard.render(),
        }
        async with aiohttp.ClientSession() as session:
            response = await session.post(url, data=data)
        if response.status != 200:
            self.logger.error("[%s:%s] Cannot edit message keyboard! Code: %s; Body: %s", self,
                              self.name, response.status, await response.text())

    def delete_message(self, chat: Chat, message: TelegramMessage):
        url = self.BASE_URL.format(token=self.token, method="deleteMessage")
        data = {"chat_id": chat.id, "message_id": message.raw["id"]}
        response = requests.post(url, data=data)
        if response.status_code != 200:
            self.logger.error("[%s:%s] Cannot delete message! Code: %s; Body: %s", self, self.name,
                              response.status_code, response.text)

    async def a_delete_message(self, chat: Chat, message: TelegramMessage):
        url = self.BASE_URL.format(token=self.token, method="deleteMessage")
        data = {"chat_id": chat.id, "message_id": message.raw["id"]}
        async with aiohttp.ClientSession() as session:
            response = await session.post(url, data=data)
        if response.status != 200:
            self.logger.error("[%s:%s] Cannot delete message! Code: %s; Body: %s", self, self.name,
                              response.status, await response.text())

    def send_chat_action(self, chat: Chat, action: str):
        url = self.BASE_URL.format(token=self.token, method="sendChatAction")
        data = {"chat_id": chat.id, "action": action}
        response = requests.post(url, data=data)
        if response.status_code != 200:
            self.logger.error("[%s:%s] Cannot send chat action! Code: %s; Body: %s", self,
                              self.name, response.status_code, response.text)

    async def a_send_chat_action(self, chat: Chat, action: str):
        url = self.BASE_URL.format(token=self.token, method="sendChatAction")
        data = {"chat_id": chat.id, "action": action}
        async with aiohttp.ClientSession() as session:
            response = await session.post(url, data=data)
        if response.status != 200:
            self.logger.error("[%s:%s] Cannot send chat action! Code: %s; Body: %s", self,
                              self.name, response.status, await response.text())

    """
    def get_me(self):
        pass

    def forward_message(self, to_chat, from_chat, message):
        pass

    def send_sticker(self, chat, sticker, **data):
        url = self.url % (self.token, "sendSticker")
        data = {"chat_id": chat.id}
        data.extend(**args)
        if hasattr(sticker, "id") and not sticker.id is None:
            data["sticker"] = sticker.id
            response = requests.post(url, data=data)
        elif not sticker.url is None:
            data["sticker"] = sticker.url
            response = requests.post(url, data=data)
        elif not sticker.file_path is None:
            with open(sticker.file_path) as f:
                response = requests.post(url, data=data, files={"sticker": f})
    
    def send_voice(self, chat, audio, **args):
        url = self.url % (self.token, "sendVoice")
        data = {"chat_id": chat.id}
        data.extend(**args)
        if hasattr(audio, "id") and not audio.id is None:
            data["voice"] = audio.id
            response = requests.post(url, data=data)
        elif not audio.url is None:
            data["voice"] = audio.url
            response = requests.post(url, data=data)
        elif not audio.file_path is None:
            with open(audio.file_path) as f:
                response = requests.post(url, data=data, files={"voice": f})
    
    def send_venue(self, chat, location, title, address, **args):
        url = self.url % (self.token, "sendLocation")
        data = {"chat_id": chat.id, "longitude": location.longitude, "latitude": location.latitude,
                "title": title, "address": address}
        data.extend(**args)
        response = requests.post(url, data=data)

    def send_contact(self, chat, attachment):
        pass
    
    def send_chat_action(self, chat, action):
        pass

    def get_user_profile_photo(self, user_id):
        pass
    
    def kick_chat_member(self, chat, user_id):
        pass
    
    def unban_chat_member(self, chat, user_id):
        pass
    
    def answer_callback_query(self, callback_query):
        pass

    def edit_message_text(self, message, text):
        pass
    
    def edit_message_caption(self, message, text):
        pass
    
    def edit_message_reply_markup(self):
        pass
    """


class TelegramUser(Chat):
    def __init__(self, agent: TelegramAgent, id: int, is_bot: bool, first_name: str,
                 last_name: (str, None)=None, username: (str, None)=None,
                 language: (str, None)=None):
        super().__init__(agent=agent, id=str(id), is_bot=is_bot, first_name=first_name,
                         last_name=last_name, username=username, language=language)

    @classmethod
    def parse(cls, agent: TelegramAgent, data: dict):
        return cls(
            agent=agent,
            id=data["id"],
            is_bot=data["is_bot"],
            first_name=data["first_name"],
            last_name=data.get("last_name"),
            username=data.get("username"),
            language=data.get("language_code"),
        )

    def render(self):
        data = {"id": self.id, "is_bot": self.raw["is_bot"], "first_name": self.raw["first_name"]}
        if "last_name" in self.raw:
            data["last_name"] = self.raw["last_name"]
        if "username" in self.raw:
            data["username"] = self.raw["username"]
        if "language" in self.raw:
            data["language_code"] = self.raw["language"]
        return data

    @property
    def is_bot(self) -> bool:
        return self.raw["is_bot"]

    @is_bot.setter
    def is_bot_setter(self, value: bool):
        self.raw["is_bot"] = value

    @property
    def first_name(self) -> str:
        return self.raw["first_name"]

    @first_name.setter
    def first_name_setter(self, value: str):
        self.raw["first_name"] = value

    @property
    def last_name(self) -> (str, None):
        return self.raw.get("last_name")

    @last_name.setter
    def last_name_setter(self, value: (str, None)):
        if value is not None:
            self.raw["last_name"] = value
        elif "last_name" in self.raw:
            del self.raw["last_name"]

    @property
    def username(self) -> (str, None):
        return self.raw.get("username")

    @username.setter
    def username_setter(self, value: (str, None)):
        if value is not None:
            self.raw["username"] = value
        elif "username" in self.raw:
            del self.raw["username"]

    @property
    def language(self) -> (str, None):
        return self.raw.get("langugage")

    @language.setter
    def language_setter(self, value: (str, None)):
        if value is not None:
            self.raw["language"] = value
        elif "language" in self.raw:
            del self.raw["language"]


class TelegramChat(Chat):
    def __init__(self, agent: TelegramAgent, id: int, type: str, title: (str, None)=None,
                 username: (str, None)=None, first_name: (str, None)=None,
                 last_name: (str, None)=None, photo: (dict, None)=None,
                 description: (str, None)=None, invite_link: (str, None)=None,
                 pinned_message: (dict, None)=None, permissions: (dict, None)=None,
                 sticker_set: (str, None)=None, can_set_sticker: (bool, None)=None):
        super().__init__(agent=agent, id=str(id), type=type, title=title, username=username,
                         first_name=first_name, last_name=last_name, photo=photo,
                         description=description, invite_link=invite_link,
                         pinned_message=pinned_message, permissions=permissions,
                         sticker_set=sticker_set, can_set_sticker=can_set_sticker)

    @classmethod
    def parse(cls, agent: TelegramAgent, data: dict):
        return cls(
            agent=agent,
            id=data["id"],
            type=data["type"],
            title=data.get("title"),
            username=data.get("username"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            photo=data.get("photo"),
            description=data.get("description"),
            invite_link=data.get("invite_link"),
            pinned_message=data.get("pinned_message"),
            permissions=data.get("permissions"),
            sticker_set=data.get("sticker_set_name"),
            can_set_sticker=data.get("can_set_sticker_set"),
        )

    def render(self):
        data = {"id": self.id, "type": self.raw["type"]}
        if "title" in self.raw:
            data["title"] = self.raw["title"]
        if "username" in self.raw:
            data["username"] = self.raw["username"]
        if "first_name" in self.raw:
            data["first_name"] = self.raw["first_name"]
        if "last_name" in self.raw:
            data["last_name"] = self.raw["last_name"]
        if "photo" in self.raw:
            data["photo"] = self.raw["photo"]
        if "description" in self.raw:
            data["description"] = self.raw["description"]
        if "invite_link" in self.raw:
            data["invite_link"] = self.raw["invite_link"]
        if "pinned_message" in self.raw:
            data["pinned_message"] = self.raw["pinned_message"]
        if "permissions" in self.raw:
            data["permissions"] = self.raw["permissions"]
        if "sticker_set" in self.raw:
            data["sticker_set_name"] = self.raw["sticker_set"]
        if "can_set_sticker" in self.raw:
            data["can_set_sticker_set"] = self.raw["can_set_sticker"]
        return data

    @property
    def type(self) -> str:
        return self.raw["type"]

    @type.setter
    def type_setter(self, value: str):
        self.raw["type"] = value

    @property
    def title(self) -> (str, None):
        return self.raw.get("title")

    @title.setter
    def title_setter(self, value: (str, None)):
        if value is not None:
            self.raw["title"] = value
        elif "title" in self.raw:
            del self.raw["title"]

    @property
    def username(self) -> (str, None):
        return self.raw.get("username")

    @username.setter
    def username_setter(self, value: (str, None)):
        if value is not None:
            self.raw["username"] = value
        elif "username" in self.raw:
            del self.raw["username"]

    @property
    def first_name(self) -> (str, None):
        return self.raw.get("first_name")

    @first_name.setter
    def first_name_setter(self, value: (str, None)):
        if value is not None:
            self.raw["first_name"] = value
        elif "first_name" in self.raw:
            del self.raw["first_name"]

    @property
    def last_name(self) -> (str, None):
        return self.raw.get("last_name")

    @last_name.setter
    def last_name_setter(self, value: (str, None)):
        if value is not None:
            self.raw["last_name"] = value
        elif "last_name" in self.raw:
            del self.raw["last_name"]

    @property
    def photo(self) -> (str, None):
        return self.raw["photo"]

    @photo.setter
    def photo_setter(self, value: (dict, None)):
        if value is not None:
            self.raw["photo"] = value
        elif "photo" in self.raw:
            del self.raw["photo"]

    @property
    def description(self) -> (str, None):
        return self.raw.get("description")

    @description.setter
    def description_setter(self, value: (str, None)):
        if value is not None:
            self.raw["description"] = value
        elif "description" in self.raw:
            del self.raw["description"]

    @property
    def invite_link(self) -> (str, None):
        return self.raw.get("invite_link")

    @invite_link.setter
    def invite_link_setter(self, value: (str, None)):
        if value is not None:
            self.raw["invite_link"] = value
        elif "invite_link" in self.raw:
            del self.raw["invite_link"]

    @property
    def pinned_message(self) -> (TelegramMessage, None):
        if "pinned_message" in self.raw:
            return TelegramMessage.parse(data=self.raw["pinned_message"])

    @pinned_message.setter
    def pinned_message_setter(self, value: (TelegramMessage, None)):
        if value is not None:
            self.raw["pinned_message"] = value.render()
        elif "pinned_message" in self.raw:
            del self.raw["pinned_message"]

    @property
    def permissions(self) -> (dict, None):
        return self.raw.get("permissions")

    @permissions.setter
    def permissions_setter(self, value: (dict, None)):
        if value is not None:
            self.raw["permissions"] = value
        elif "permissions" in self.raw:
            del self.raw["permissons"]

    @property
    def sticker_set(self) -> (str, None):
        return self.raw.get("sticker_set")

    @sticker_set.setter
    def sticker_set_setter(self, value: (str, None)):
        if value is not None:
            self.raw["sticker_set"] = value
        elif "sticker_set" in self.raw:
            del self.raw["sticker_set"]

    @property
    def can_set_sticker(self) -> (bool, None):
        return self.raw.get("can_set_sticker")

    @can_set_sticker.setter
    def can_set_sticker_setter(self, value: (bool, None)):
        if value is not None:
            self.raw["can_set_sticker"] = value
        elif "can_set_sticker" in self.raw:
            del self.raw["can_set_sticker"]


# Нужны остальные необязательные поля
class TelegramMessage(Message):
    def __init__(self, id: int, datetime: int, chat: dict, text: (str, None)=None,
                 images: Iterator[Attachment]=[], audios: Iterator[Attachment]=[],
                 videos: Iterator[Attachment]=[], documents: Iterator[Attachment]=[],
                 locations: Iterator[Location]=[]):
        super().__init__(id=id, datetime=datetime, chat=chat, text=text, images=images,
                         audios=audios, videos=videos, documents=documents, locations=locations)

    @classmethod
    def parse(cls, data: dict, agent: (TelegramAgent, None)=None):
        images = []
        audios = []
        videos = []
        documents = []
        locations = []
        if "photo" in data:
            images.append(TelegramAttachment.parse(data=data["photo"][-1], agent=agent))
        if "audio" in data:
            audios.append(TelegramAttachment.parse(data=data["audio"], agent=agent))
        if "video" in data:
            videos.append(TelegramAttachment.parse(data=data["video"], agent=agent))
        if "document" in data:
            documents.append(TelegramAttachment.parse(data=data["document"], agent=agent))
        if "location" in data:
            locations.append(TelegramLocation.parse(data=data["location"]))
        return cls(
            id=data["message_id"],
            datetime=data["date"],
            chat=data.get("chat"),
            text=data.get("text"),
            images=images,
            audios=audios,
            videos=videos,
            documents=documents,
            locations=locations,
        )

    @classmethod
    async def a_parse(cls, data: dict, agent: (TelegramAgent, None)=None):
        images = []
        audios = []
        videos = []
        documents = []
        locations = []
        if "photo" in data:
            images.append(await TelegramAttachment.a_parse(data=data["photo"][-1], agent=agent))
        if "audio" in data:
            audios.append(await TelegramAttachment.a_parse(data=data["audio"], agent=agent))
        if "video" in data:
            videos.append(await TelegramAttachment.a_parse(data=data["video"], agent=agent))
        if "document" in data:
            documents.append(await TelegramAttachment.a_parse(data=data["document"], agent=agent))
        if "location" in data:
            locations.append(TelegramLocation.parse(data=data["location"]))
        return cls(
            id=data["message_id"],
            datetime=data["date"],
            chat=data["chat"],
            text=data.get("text"),
            images=images,
            audios=audios,
            videos=videos,
            documents=documents,
            locations=locations,
        )

    def render(self):
        data = {
            "message_id": self.raw["id"],
            "date": self.raw["datetime"],
            "chat": self.raw["chat"],
        }
        if self.text is not None:
            data["text"] = self.text
        return data

    @property
    def id(self) -> int:
        return self.raw["id"]

    @id.setter
    def id_setter(self, value: int):
        self.raw["id"] = value

    @property
    def datetime(self) -> datetime:
        return datetime.utcfromtimestamp(self.raw["datetime"])

    @datetime.setter
    def datetime_setter(self, value: datetime):
        self.raw["datetime"] = datetime.timestamp()

    @property
    def chat(self) -> Chat:
        return TelegramChat.parse(agent=None, data=self.raw["chat"])

    @chat.setter
    def chat_setter(self, value: TelegramChat):
        self.raw["chat"] = value.render()


class TelegramCallback(Message):
    def __init__(self, id: str, user: dict, message: (dict, None)=None,
                 inline_message_id: (str, None)=None, chat_instance: (str, None)=None,
                 data: (str, None)=None, game_short_name: (str, None)=None):
        super().__init__(id=id, text=data, user=user, message=message,
                         inline_message_id=inline_message_id, chat_instance=chat_instance,
                         game_short_name=game_short_name)

    @classmethod
    def parse(cls, data: dict):
        return cls(
            id=data["id"],
            user=data["from"],
            message=data.get("message"),
            inline_message_id=data.get("inline_message_id"),
            chat_instance=data.get("chat_instance"),
            data=data.get("data"),
            game_short_name=data.get("game_short_name"),
        )

    def render(self):
        data = {"id": self.raw["id"], "from": self.raw["user"]}
        if "message" in self.raw:
            data["message"] = self.raw["message"]
        if "inline_message_id" in self.raw:
            data["inline_message_id"] = self.raw["inline_message_id"]
        if "chat_instance" in self.raw:
            data["chat_instance"] = self.raw["chat_instance"]
        if "data" in self.raw:
            data["data"] = self.raw["data"]
        if "game_short_name" in self.raw:
            data["game_short_name"] = self.raw["game_short_name"]

    @property
    def id(self) -> str:
        return self.raw["id"]

    @id.setter
    def id_setter(self, value: str):
        self.raw["id"] = value

    @property
    def user(self) -> dict:
        return self.raw["user"]

    @user.setter
    def user_setter(self, value: dict):
        self.raw["user"] = value

    @property
    def message(self) -> (TelegramMessage, None):
        if "message" in self.raw:
            return TelegramMessage.parse(data=self.raw["message"])
        else:
            return None

    @message.setter
    def message_setter(self, value: (TelegramMessage, None)):
        if value is not None:
            self.raw["message"] = value.render()
        elif "message" in self.raw:
            del self.raw["message"]

    @property
    def inline_message_id(self) -> (str, None):
        return self.raw.get("inline_message_id")

    @inline_message_id.setter
    def inline_message_id_setter(self, value: (str, None)):
        if value is not None:
            self.raw["inline_message_id"] = value
        elif "inline_message_id" in self.raw:
            del self.raw["inline_message_id"]

    @property
    def chat_instance(self) -> (str, None):
        return self.raw.get("chat_instance")

    @chat_instance.setter
    def chat_instance_setter(self, value: (str, None)):
        if value is not None:
            self.raw["chat_instance"] = value
        elif "chat_instance" in self.raw:
            del self.raw["chat_instance"]

    @property
    def data(self) -> (str, None):
        return self.raw.get("data")

    @data.setter
    def data_setter(self, value: (str, None)):
        if value is not None:
            self.raw["data"] = value
        elif "data" in self.raw:
            del self.raw["data"]

    @property
    def game_short_name(self) -> (str, None):
        return self.raw.get("game_short_name")

    @game_short_name.setter
    def game_short_name_setter(self, value: (str, None)):
        if value is not None:
            self.raw["game_short_name"] = value
        elif "game_short_name" in self.raw:
            del self.raw["game_short_name"]


class TelegramAttachment(Attachment):
    def __init__(self, url: (str, None)=None, filepath: (str, None)=None, id: (str, None)=None,
                 size: (int, None)=None):
        super().__init__(url=url, filepath=filepath, id=id, size=size)

    @classmethod
    def parse(cls, data: dict, agent: (TelegramAgent, None)):
        if agent is None:
            url = None
        else:
            file_path = agent.get_file(data["file_id"])["result"]["file_path"]
            url = agent.FILE_URL.format(token=agent.token, file_path=file_path),
        return cls(id=data["file_id"], url=url, size=data["file_size"])

    @classmethod
    async def a_parse(cls, data: dict, agent: (TelegramAgent, None)=None):
        if agent is None:
            url = None
        else:
            file_path = (await agent.a_get_file(data["file_id"]))["result"]["file_path"]
            url = agent.FILE_URL.format(token=agent.token, file_path=file_path)
        return cls(id=data["file_id"], url=url, size=data["file_size"])

    @property
    def id(self):
        return self.raw["id"]

    @id.setter
    def id_setter(self, value: (str, None)):
        if id is not None:
            self.raw["id"] = id
        else:
            del self.raw["id"]

    @property
    def size(self):
        return self.raw["size"]

    @size.setter
    def size_setter(self, value: (int, None)):
        if value is not None:
            self.raw["size"] = value
        else:
            del self.raw["size"]


# STOP HERE


class TelegramLocation(Location):
    def __init__(self, latitude: float, longitude: float):
        super().__init__(latitude=latitude, longitude=longitude)

    @classmethod
    def parse(cls, data: dict):
        return cls(latitude=data["latitude"], longitude=data["longitude"])


class TelegramVenue(Location):
    def __init__(self, latitude: float, longitude: float):
        super().__init__(latitude=latitude, longitude=longitude)

    @classmethod
    def parse(cls, data: dict):
        return cls(latitude=data["latitude"], longitude=data["longitude"])


class TelegramKeyboard(Keyboard):
    def __init__(self, buttons: Iterator[Iterator[KeyboardButton]], resize: bool=False,
                 one_time: bool=False, selective: bool=False):
        super().__init__(buttons=buttons, resize=resize, one_time=one_time, selective=selective)

    def render(self):
        data = {
            "keyboard": [],
            "resize_keyboard": self.raw["resize"],
            "one_time_keyboard": self.raw["one_time"],
            "selective": self.raw["selective"],
        }
        for line in self.buttons:
            line_data = []
            data["keyboard"].append(line_data)
            for button in line:
                if hasattr(button, "render"):
                    line_data.append(button.render())
                else:
                    line_data.append(button.text)
        return json.dumps(data)

    @staticmethod
    def default_render(keyboard: Keyboard):
        data = {"keyboard": []}
        for line in keyboard.buttons:
            line_data = []
            data["keyboard"].append(line_data)
            for button in line:
                line_data.append(button.text)
        return json.dumps(data)


class TelegramInlineKeyboard(Keyboard):
    def __init__(self, buttons: Iterator[Iterator[TelegramInlineKeyboardButton]]):
        super().__init__(buttons=buttons)

    def render(self):
        data = {"inline_keyboard": []}
        for line in self.buttons:
            line_data = []
            data["inline_keyboard"].append(line_data)
            for button in line:
                line_data.append(button.render())
        return json.dumps(data)

class TelegramKeyboardButton(KeyboardButton):
    def __init__(self, text: str, contact: bool=False, location: bool=False):
        super().__init__(text=text, contact=contact, location=location)

    def render(self):
        return {
            "text": self.text,
            "request_contact": self.raw["contact"],
            "request_location": self.raw["location"],
        }

class TelegramInlineKeyboardButton(KeyboardButton):
    def __init__(self, text: str, url: (str, None)=None, data: (str, None)=None,
                 inline_query: (str, None)=None, inline_chat: (str, None)=None,
                 game: dict={}):
        super().__init__(text=text, url=url, data=data, inline_query=inline_query,
                         inline_chat=inline_chat, game=game)

    def render(self):
        data = {"text": self.text, "callback_game": self.raw["game"]}
        if "url" in self.raw:
            data["url"] = self.raw["url"]
        if "data" in self.raw:
            data["callback_data"] = self.raw["data"]
        if "inline_query" in self.raw:
            data["switch_inline_query"] = self.raw["inline_query"]
        if "inline_chat" in self.raw:
            data["switch_inline_query_current_chat"] = self.raw["inline_chat"]
        return data
