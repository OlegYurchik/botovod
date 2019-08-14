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

    url = "https://api.telegram.org/bot{token}/{method}"

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
            message = TelegramMessage.parse(agent=self, data=update["message"])
            messages.append((chat, message))
        if "callback_query" in update:
            data = update["callback_data"]
            if "message" in data:
                chat = TelegramChat.parse(agent=self, data=data["message"]["chat"])
            else:
                chat = TelegramUser.parse(agent=self, data=data["from"])
            message = TelegramCallback.parse(data=update["callback_data"])
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
            message = await TelegramMessage.a_parse(agent=self, data=update["message"])
            messages.append((chat, message))
        if "callback_query" in update:
            data = update["callback_data"]
            if "message" in data:
                chat = TelegramChat.parse(agent=self, data=data["message"]["chat"])
            else:
                chat = TelegramUser.parse(agent=self, data=data["from"])
            message = TelegramCallback.parse(data=update["callback_data"])
            messages.append((chat, message))
        return messages

    def responser(self, headers: Dict[str, str], body: str) -> Tuple[int, Dict[str, str], str]:
        return 200, {}, ""

    async def a_responser(self, headers: Dict[str, str],
                          body: str) -> Tuple[int, Dict[str, str], str]:
        return self.responser(headers=headers, body=body)

    def polling(self):
        url = self.url.format(token=self.token, method="getUpdates")
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
        url = self.url.format(token=self.token, method="getUpdates")
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

    def send_attachment(self, type: str, chat: Chat, attachment: Attachment, **raw):
        url = self.url.format(token=self.token, method="send" + type.capitalize())
        data = {"chat_id": chat.id}
        if "id" in attachment.raw:
            data["file_id"] = attachment.raw["id"]
        elif attachment.url is not None:
            data[type] = attachment.url
            response = requests.post(url, data=data)
        elif attachment.filepath is not None:
            data[type] = open(attachment.filepath)
        else:
            return
        data.update(raw)
        response = requests.post(url, data=data)
        if response.status_code != 200:
            self.logger.error("[%s:%s] Cannot send photo! Code: %s; Body: %s", self, self.name,
                              response.status_code, response.text)

    async def a_send_attachment(self, type: str, chat: Chat, attachment: Attachment, **raw):
        url = self.url.format(token=self.token, method="send" + type.capitalize())
        data = {"chat_id": chat.id}
        if "id" in attachment.raw:
            data["file_id"] = attachment.raw["id"]
        elif attachment.url is not None:
            data[type] = attachment.url
            response = requests.post(url, data=data)
        elif attachment.filepath is not None:
            data[type] = open(attachment.filepath)
        else:
            return
        data.update(raw)
        async with aiohttp.ClientSession() as session:
            response = await session.post( url, data=data)
        if response.status != 200:
            self.logger.error("[%s:%s] Cannot send photo! Code: %s; Body: %s", self, self.name,
                              response.status, await response.text())

    def set_webhook(self):
        self.logger.info("[%s:%s] Setting webhook...", self, self.name)

        url = self.url.format(token=self.token, method="setWebhook")
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

        url = self.url.format(token=self.token, method="setWebhook")
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
        if text is not None:
            url = self.url.format(token=self.token, method="sendMessage")
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
        for image in images:
            self.send_photo(chat, image)
        for audio in audios:
            self.send_audio(chat, audio)
        for document in documents:
            self.send_document(chat, document)
        for video in videos:
            self.send_video(chat, video)
        for location in locations:
            self.send_location(chat, location)

    async def a_send_message(self, chat: Chat, text: (str, None)=None,
                             images: Iterator[Attachment]=[], audios: Iterator[Attachment]=[],
                             documents: Iterator[Attachment]=[], videos: Iterator[Attachment]=[],
                             locations: Iterator[Location]=[], keyboard: (Keyboard, None)=None,
                             mode: (str, None)=None, web_preview: bool=True,
                             notification: bool=True, reply: (Message, None)=None):
        if text is not None:
            url = self.url.format(token=self.token, method="sendMessage")
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
                logging.error("[%s:%s] Cannot send message! Code: %s; Body: %s", self,
                                  self.name, response.status, await response.text())
        for image in images:
            await self.a_send_photo(chat, image)
        for audio in  audios:
            await self.a_send_audio(chat, audio)
        for document in documents:
            await self.a_send_document(chat, document)
        for video in videos:
            await self.a_send_video(chat, video)
        for location in locations:
            await self.a_send_location(chat, location)

    def send_photo(self, chat: Chat, image: Attachment):
        return self.send_attachment(agent=self, type="photo", chat=chat, attachment=image)

    async def a_send_photo(self, chat: Chat, image: Attachment):
        return await self.a_send_attachment(agent=self, type="photo", chat=chat, attachment=image)

    def send_audio(self, chat: Chat, audio: Attachment):
        return self.send_attachment(agent=self, type="audio", chat=chat, attachment=audio)

    async def a_send_audio(self, chat: Chat, audio: Attachment):
        return await self.a_send_attachment(agent=self, type="audio", chat=chat, attachment=audio)

    def send_document(self, chat: Chat, document: Attachment):
        return self.send_attachment(agent=self, type="document", chat=chat, attachment=document)

    async def a_send_document(self, chat: Chat, document: Attachment):
        return await self.a_send_attachment(agent=self, type="document", chat=chat,
                                            attachment=document)

    def send_video(self, chat: Chat, video: Attachment):
        return self.send_attachment(agent=self, type="video", chat=chat, attachment=video)

    async def a_send_video(self, chat: Chat, video: Attachment):
        return await self.a_send_attachment(agent=self, type="video", chat=chat, attachment=video)

    def send_location(self, chat: Chat, location: Location):
        url = self.url.format(token=self.token, method="sendLocation")
        data = {"chat_id": chat.id, "longitude": location.longitude, "latitude": location.latitude}
        response = requests.post(url, data=data)
        if response.status_code != 200:
            self.logger.error("[%s:%s] Cannot send location! Code: %s; Body: %s", self, self.name,
                              response.status_code, response.text)

    async def a_send_location(self, chat: Chat, location: Location):
        url = self.url.format(token=self.token, method="sendLocation")
        data = {"chat_id": chat.id, "longitude": location.longitude, "latitude": location.latitude}
        async with aiohttp.ClientSession() as session:
            response = await session.post(url, data=data)
        if response.status != 200:
            self.logger.error("[%s:%s] Cannot send location! Code: %s; Body: %s", self, self.name,
                              response.status, await response.text())

    def get_file(self, file_id: int):
        url = self.url.format(token=self.token, method="getFile")
        response = requests.get(url, params={"file_id": file_id})
        if response.status_code != 200:
            self.logger.error("[%s:%s] Cannot get file! Code: %s; Body: %s", self, self.name,
                              response.status_code, response.text)
        return response.json()

    async def a_get_file(self, file_id: int):
        url = self.url.format(token=self.token, method="getFile")
        async with aiohttp.ClientSession() as session:
            response = await session.get(url, params={"file_id": file_id})
        if response.status != 200:
            self.logger.error("[%s:%s] Cannot get file! Code: %s; Body: %s", self, self.name,
                              response.status, await response.text())
        return await response.json()

    def edit_message(self, chat: Chat, message: Message, text: (str, None)=None,
                     images: Iterator[Attachment]=[], audios: Iterator[Attachment]=[],
                     documents: Iterator[Attachment]=[], videos: Iterator[Attachment]=[],
                     locations: Iterator[Location]=[], keyboard: (Keyboard, None)=None,
                     caption: (str, None)=None):
        if text:
            url = self.url.format(token=self.token, method="editMessageText")
            data = {"chat_id": chat.id, "message_id": message.id, "text": message.text}
            if keyboard is not None:
                if hasattr(keyboard, "render"):
                    data["reply_markup"] = keyboard.render()
                else:
                    data["reply_markup"] = TelegramKeyboard.default_render(keyboard)
            response = requests.post(url, data=data)
        elif isinstance(keyboard, TelegramInlineKeyboard):
            url = self.url.format(token=self.token, method="editMessageReplyMarkup")
            data = {"chat_id": chat.id, "message_id": message.id}
            data["reply_markup"] = keyboard.render()
            response = requests.post(url, data=data)
        if response.status_code != 200:
            self.logger.error("[%s:%s] Cannot send message! Code: %s; Body: %s", self,
                                self.name, response.status_code, response.text)
        if caption is not None:
            url = self.url.format(token=self.token, method="editMessageCaption")
            data = {"chat_id": chat.id, "message_id": message.id, "caption": caption}
            response = requests.post(url, data=data)
            if response.status_code != 200:
                self.logger.error("[%s:%s] Cannot send message! Code: %s; Body: %s", self,
                                  self.name, response.status_code, response.text)

    async def a_edit_message(self, chat: Chat, message: Message, text: (str, None)=None,
                             images: Iterator[Attachment]=[], audios: Iterator[Attachment]=[],
                             documents: Iterator[Attachment]=[], videos: Iterator[Attachment]=[],
                             locations: Iterator[Location]=[], keyboard: (Keyboard, None)=None,
                             caption: (str, None)=None):
        if text:
            url = self.url.format(token=self.token, method="editMessageText")
            data = {"chat_id": chat.id, "message_id": message.id, "text": message.text}
            if keyboard is not None:
                if hasattr(keyboard, "render"):
                    data["reply_markup"] = keyboard.render()
                else:
                    data["reply_markup"] = TelegramKeyboard.default_render(keyboard)
            async with aiohttp.ClientSession() as session:
                response = await session.post(url, data=data)
        elif isinstance(keyboard, TelegramInlineKeyboard):
            url = self.url.format(token=self.token, method="editMessageReplyMarkup")
            data = {
                "chat_id": chat.id,
                "message_id": message.id,
                "reply_markup": keyboard.render(),
            }
            async with aiohttp.ClientSession() as session:
                response = await session.post(url, data=data)
        if response.status != 200:
            self.logger.error("[%s:%s] Cannot send message! Code: %s; Body: %s", self,
                                self.name, response.status, await response.text())
        if caption is not None:
            url = self.url.format(token=self.token, method="editMessageCaption")
            data = {"chat_id": chat.id, "message_id": message.id, "caption": caption}
            async with aiohttp.ClientSession() as session:
                response = await session.post(url, data=data)
            if response.status != 200:
                self.logger.error("[%s:%s] Cannot send message! Code: %s; Body: %s", self,
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
    
    def get_file(self, file_id):
        url = self.url % (self.token, "getFile")
        response = requests.get(url, data = {"file_id": file_id})
        return response.text

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
    def __init__(self, agent: TelegramAgent, id: int, bot: bool, first_name: str,
                 last_name: (str, None)=None, username: (str, None)=None,
                 language: (str, None)=None):
        super().__init__(agent=agent, id=username or str(id), bot=bot, first_name=first_name,
                         last_name=last_name, username=username, language=language, user_id=id)

    @classmethod
    def parse(cls, agent: TelegramAgent, data: dict):
        return cls(
            agent=agent,
            id=data["id"],
            bot=data["is_bot"],
            first_name=data.get["first_name"],
            last_name=data.get("last_name"),
            username=data.get("username"),
            language=data.get("language_code"),
        )

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


class TelegramMessage(Message):
    def __init__(self, id: str, datetime: datetime, chat: dict, text: (str, None)=None,
                 images: Iterator[Attachment]=[], audios: Iterator[Attachment]=[],
                 videos: Iterator[Attachment]=[], documents: Iterator[Attachment]=[],
                 locations: Iterator[Location]=[]):
        super().__init__(id=id, datetime=datetime, chat=chat, text=text, images=images,
                         audios=audios, videos=videos, documents=documents, locations=locations)

    @classmethod
    def parse(cls, agent: TelegramAgent, data: dict, load_attachments: bool=False):
        images = []
        audios = []
        videos = []
        documents = []
        locations = []
        for photo in data.get("photo", []):
            images.append(TelegramAttachment.parse(agent=agent, data=photo,
                                                   load_attachments=load_attachments))
        if "audio" in data:
            audios.append(TelegramAttachment.parse(agent=agent, data=data["audio"],
                                                   load_attachments=load_attachments))
        if "video" in data:
            videos.append(TelegramAttachment.parse(agent=agent, data=data["video"],
                                                   load_attachments=load_attachments))
        if "document" in data:
            documents.append(TelegramAttachment.parse(agent=agent, data=data["document"],
                                                      load_attachments=load_attachments))
        if "location" in data:
            locations.append(TelegramLocation.parse(data=data["location"]))
        return cls(
            id=data["message_id"],
            datetime=datetime.utcfromtimestamp(data["date"]),
            chat=data.get("chat"),
            text=data.get("text"),
            images=images,
            audios=audios,
            videos=videos,
            documents=documents,
            locations=locations,
        )

    @classmethod
    async def a_parse(cls, agent: TelegramAgent, data: dict, load_attachments: bool=False):
        images = []
        audios = []
        videos = []
        documents = []
        locations = []
        for photo in data.get("photo", []):
            images.append(await TelegramAttachment.a_parse(agent=agent, data=photo,
                                                           load_attachments=load_attachments))
        if "audio" in data:
            audios.append(await TelegramAttachment.a_parse(agent=agent, data=data["audio"],
                                                           load_attachments=load_attachments))
        if "video" in data:
            videos.append(await TelegramAttachment.a_parse(agent=agent, data=data["video"],
                                                           load_attachments=load_attachments))
        if "document" in data:
            documents.append(await TelegramAttachment.a_parse(agent=agent, data=data["document"],
                                                              load_attachments=load_attachments))
        if "location" in data:
            locations.append(TelegramLocation.parse(data=data["location"]))
        return cls(
            id=data["message_id"],
            datetime=datetime.utcfromtimestamp(data["date"]),
            chat=TelegramChat.parse(agent=agent, data=data["chat"]),
            text=data.get("text"),
            images=images,
            audios=audios,
            videos=videos,
            documents=documents,
            locations=locations,
        )


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
            id=data["message_id"],
            user=data["from"],
            message=data.get("message"),
            inline_message_id=data.get("inline_message_id"),
            chat_instance=data.get("chat_instance"),
            data=data.get("data"),
            game_short_name=data.get("game_short_name"),
        )


class TelegramAttachment(Attachment):
    def __init__(self, url: (str, None)=None, filepath: (str, None)=None, id: (str, None)=None,
                 size: (int, None)=None):
        super().__init__(url=url, filepath=filepath, id=id, size=size)

    @classmethod
    def parse(cls, agent: TelegramAgent, data: dict, load_attachments: bool=False):
        if load_attachments:
            url = agent.get_file(data["file_id"])["result"]["file_path"]
        else:
            url = None
        return cls(
            id=data["file_id"],
            url=None if url is None else agent.url.format(token=agent.token, method=url),
            size=data["file_size"],
        )

    @classmethod
    async def a_parse(cls, agent: TelegramAgent, data: dict, load_attachments: bool=False):
        if load_attachments:
            url = await agent.a_get_file(data["file_id"])["result"]["file_path"]
        else:
            url = None
        return cls(
            id=data["file_id"],
            url=None if url is None else agent.url.format(token=agent.token, method=url),
            size=data["file_size"],
        )


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
    def __init__(self, buttons: Iterator[Iterator[TelegramKeyboardButton]], resize: bool=False,
                 one_time: bool=False, selective: bool=False):
        super().__init__(buttons=buttons, resize=resize, one_time=one_time, selective=selective)

    def render(self):
        data = {
            "keyboard": [],
            "resize_keyboard": self.resize,
            "one_time_keyboard": self.one_time,
            "selective": self.selective,
        }
        for line in self.buttons:
            line_data = []
            data["keyboard"].append(line_data)
            for button in line:
                line_data.append(button.render())
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
    def __init__(self, buttons: Iterator[Iterator[TelegramKeyboardButton]]):
        super().__init__(buttons=buttons)

    def render(self):
        data = {"inline_keyboard": []}
        for line in self.buttons:
            line_data = []
            data["keyboard"].append(line_data)
            for button in line:
                line_data.append(button.render())
        return json.dumps(data)

class TelegramKeyboardButton(KeyboardButton):
    def __init__(self, text: str, contact: bool=False, location: bool=False):
        super().__init__(text=text, contact=contact, location=location)

    def render(self):
        return {
            "text": self.text,
            "request_contact": self.contact,
            "request_location": self.location,
        }

class TelegramInlineKeyboardButton(KeyboardButton):
    def __init__(self, text: str, url: (str, None)=None, data: (str, None)=None,
                 inline_query: (str, None)=None, inline_chat: (str, None)=None,
                 game: dict={}):
        super().__init__(text=text, url=url, data=data, inline_query=inline_query,
                         inline_chat=inline_chat, game=game)

    def render(self):
        data = {"text": self.text, "callback_game": self.game}
        if self.url is not None:
            data["url"] = self.url
        if self.data is not None:
            data["callback_data"] = self.data
        if self.inline_query is not None:
            data["switch_inline_query"] = self.inline_query
        if self.inline_chat is not None:
            data["switch_inline_query_current_chat"] = self.inline_chat
        return data
        