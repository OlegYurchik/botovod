from __future__ import annotations
import aiofiles
import aiohttp
import asyncio
from botovod import utils
from botovod.agents import (Agent, Attachment, Audio, Chat, Document, Image, Keyboard, Location,
                            Message, Video)
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

    def parser(self, headers: Dict[str, str], body: str) -> List[Tuple[Chat, TelegramMessage]]:
        update = json.loads(body)
        messages = []
        if update["update_id"] <= self.last_update:
            return messages
        self.last_update = update["update_id"]
        if "message" in update:
            message_data = update["message"]
            chat_data = message_data["chat"]

            chat = Chat(self, str(chat_data["id"]))
            chat.custom = chat_data
            message = TelegramMessage()
            message.parser(self, message_data)
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
            message_data = update["message"]
            chat_data = message_data["chat"]

            chat = Chat(self, str(chat_data["id"]))
            chat.custom = chat_data
            message = TelegramMessage()
            await message.a_parser(self, message_data)
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
                updates = await response.json()["result"]
                for update in updates:
                    await self.a_listen(dict(response.headers), json.dumps(update))
            except Exception:
                self.logger.exception("[%s:%s] Got exception")
                self.logger.error("[%s:%s] Get incorrect update! Code: %s. Response: %s", self,
                                  self.name, response.status, await response.text())
            finally:
                await asyncio.sleep(self.delay)

    def set_webhook(self):
        self.logger.info("[%s:%s] Setting webhook...", self, self.name)

        url = self.url.format(token=self.token, method="setWebhook")
        data, files = {}, {}
        if self.method == self.WEBHOOK:
            data["url"] = self.webhook_url
            if self.certificate_path is not None:
                files["certificate"] = open(self.certificate_path)
        response = requests.post(url, data=data, files=files)
        if response.status_code != 200:
            self.logger.error("[%s:%s] Webhook doesn't set! Code: %s; Body: %s", self, self.name,
                              response.status_code, response.text)
            return

        self.logger.info("[%s:%s] Set webhook.", self, self.name)

    async def a_set_webhook(self):
        self.logger.info("[%s:%s] Setting webhook...", self, self.name)

        url = self.url.format(token=self.token, method="setWebhook")
        data, files = {}, {}
        if self.method == self.WEBHOOK:
            data["url"] = self.webhook_url
            if self.certificate_path is not None:
                files["certificate"] = open(self.certificate_path)
        async with aiohttp.ClientSession() as session:
            response = await session.post(url, data=data)
        if response.status_code != 200:
            self.logger.error("[%s:%s] Webhook doesn't set! Code: %s; Body: %s", self, self.name,
                              response.status_code, response.text)
            return

        self.logger.info("[%s:%s] Set webhook.", self, self.name)

    def send_message(self, chat: Chat, text: (str, None)=None, images: Iterator[Image]=[],
                     audios: Iterator[Audio]=[], documents: Iterator[Document]=[],
                     videos: Iterator[Video]=[], locations: Iterator[Location]=[],
                     keyboard: (Keyboard, None)=None, raw: (Dict[str, str], None)=None):
        if text is not None:
            url = self.url.format(token=self.token, method="sendMessage")
            data = {"chat_id": chat.id, "text": text}
            if not keyboard is None:
                data["reply_markup"] = json.dumps({
                    "keyboard": [[button.text] for button in keyboard.buttons],
                    "resize_keyboard": True,
                })
            if raw is not None:
                data.update(**raw)
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

    async def a_send_message(self, chat: Chat, text: (str, None)=None, images: Iterator[Image]=[],
                             audios: Iterator[Audio]=[], documents: Iterator[Document]=[],
                             videos: Iterator[Video]=[], locations: Iterator[Location]=[],
                             keyboard: (Keyboard, None)=None, raw: (Dict[str, str], None)=None):
        if text is not None:
            url = self.url.format(token=self.token, method="sendMessage")
            data = {"chat_id": chat.id, "text": text}
            if not keyboard is None:
                data["reply_markup"] = json.dumps({
                    "keyboard": [[button.text] for button in keyboard.buttons],
                    "resize_keyboard": True,
                })
            if raw is not None:
                data.update(**raw)
            async with aiohttp.ClientSession() as session:
                response = await session.post(url, data=data)
            if response.status != 200:
                self.logger.error("[%s:%s] Cannot send message! Code: %s; Body: %s", self,
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

    def send_photo(self, chat: Chat, image: Image):
        url = self.url.format(token=self.token, method="sendPhoto")
        data = {"chat_id": chat.id}
        if "file_id" in image.raw:
            data["photo"] = image.raw["file_id"]
            response = requests.post(url, data=data)
        elif image.url is not None:
            data["photo"] = image.url
            response = requests.post(url, data=data)
        elif image.file_path is not None:
            with open(image.file_path) as file:
                response = requests.post(url, data=data, files={"photo": file})
        else:
            return
        if response.status_code != 200:
            self.logger.error("[%s:%s] Cannot send photo! Code: %s; Body: %s", self, self.name,
                              response.status_code, response.text)

    async def a_send_photo(self, chat: Chat, image: Image):
        url = self.url.format(token=self.token, method="sendPhoto")
        data = {"chat_id": chat.id}
        if "file_id" in image.raw:
            data["photo"] = image.raw["file_id"]
            async with aiohttp.ClientSession() as session:
                response = await session.post(url, data=data)
        elif image.url is not None:
            data["photo"] = image.url
            async with aiohttp.ClientSession() as session:
                response = await session.post(url, data=data)
        elif image.file_path is not None:
            async with aiohttp.ClientSession() as session:
                async with aiofiles.open(image.file_path) as file:
                    response = session.post(url, data=data)
        else:
            return
        if response.status != 200:
            self.logger.error("[%s:%s] Cannot send photo! Code: %s; Body: %s", self, self.name,
                              response.status, await response.text())

    def send_audio(self, chat: Chat, audio: Audio):
        url = self.url.format(token=self.token, method="sendAudio")
        data = {"chat_id": chat.id}
        if "file_id" in audio.raw:
            data["audio"] = audio.raw["file_id"]
            response = requests.post(url, data=data)
        elif not audio.url is None:
            data["audio"] = audio.url
            response = requests.post(url, data=data)
        elif not audio.file_path is None:
            with open(audio.file_path) as file:
                response = requests.post(url, data=data, files={"audio": file})
        else:
            return
        if response.status_code != 200:
            self.logger.error("[%s:%s] Cannot send audio! Code: %s; Body: %s", self, self.name,
                              response.status_code, response.text)

    async def a_send_audio(self, chat: Chat, audio: Audio):
        url = self.url.format(token=self.token, method="sendAudio")
        data = {"chat_id": chat.id}
        if "file_id" in audio.raw:
            data["audio"] = audio.raw["file_id"]
            async with aiohttp.ClientSession() as session:
                response = await session.post(url, data=data)
        elif not audio.url is None:
            data["audio"] = audio.url
            async with aiohttp.ClientSession() as session:
                response = await session.post(url, data=data)
        elif not audio.file_path is None:
            async with aiohttp.ClientSession() as session:
                async with aiofiles.open(audio.file_path) as file:
                    response = await session.post(url, data=data)
        else:
            return
        if response.status != 200:
            self.logger.error("[%s:%s] Cannot send audio! Code: %s; Body: %s", self, self.name,
                              response.status, await response.text())

    def send_document(self, chat: Chat, document: Document):
        url = self.url.format(token=self.token, method="sendDocument")
        data = {"chat_id": chat.id}
        if "file_id" in document.raw:
            data["document"] = document.raw["file_id"]
            response = requests.post(url, data=data)
        elif not document.url is None:
            data["document"] = document.url
            response = requests.post(url, data=data)
        elif not document.file_path is None:
            with open(document.file_path) as file:
                response = requests.post(url, data=data, files={"document": file})
        else:
            return
        if response.status_code != 200:
            self.logger.error("[%s:%s] Cannot send document! Code: %s; Body: %s", self, self.name,
                              response.status_code, response.text)

    async def a_send_document(self, chat: Chat, document: Document):
        url = self.url.format(token=self.token, method="sendDocument")
        data = {"chat_id": chat.id}
        if "file_id" in document.raw:
            data["document"] = document.raw["file_id"]
            async with aiohttp.ClientSession() as session:
                response = await session.post(url, data=data)
        elif not document.url is None:
            data["document"] = document.url
            async with aiohttp.ClientSession() as session:
                response = await session.post(url, data=data)
        elif not document.file_path is None:
            async with aiohttp.ClientSession() as session:
                with open(document.file_path) as file:
                    response = await session.post(url, data=data)
        else:
            return
        if response.status != 200:
            self.logger.error("[%s:%s] Cannot send document! Code: %s; Body: %s", self, self.name,
                              response.status, await response.text())

    def send_video(self, chat: Chat, video: Video):
        url = self.url.format(token=self.token, method="sendVideo")
        data = {"chat_id": chat.id}
        if "file_id" in video.raw:
            data["video"] = video.raw["file_id"]
            response = requests.post(url, data=data)
        elif not video.url is None:
            data["video"] = video.url
            response = requests.post(url, data=data)
        elif not video.file_path is None:
            with open(video.file_path) as file:
                response = requests.post(url, data=data, files={"video": file})
        else:
            return
        if response.status_code != 200:
            self.logger.error("[%s:%s] Cannot send video! Code: %s; Body: %s", self, self.name,
                              response.status_code, response.text)

    async def a_send_video(self, chat: Chat, video: Video):
        url = self.url.format(token=self.token, method="sendVideo")
        data = {"chat_id": chat.id}
        if "file_id" in video.raw:
            data["video"] = video.raw["file_id"]
            async with aiohttp.ClientSession() as session:
                response = await session.post(url, data=data)
        elif not video.url is None:
            data["video"] = video.url
            async with aiohttp.ClientSession() as session:
                response = await session.post(url, data=data)
        elif not video.file_path is None:
            async with aiohttp.ClientSession() as session:
                async with aiofiles.open(video.file_path) as file:
                    response = await session.post(url, data=data)
        else:
            return
        if response.status != 200:
            self.logger.error("[%s:%s] Cannot send video! Code: %s; Body: %s", self, self.name,
                              response.status, await response.text())

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


class TelegramAttachment(Attachment):
    def parser(self, agent: TelegramAgent, data: dict):
        file_path = agent.get_file(data["file_id"])["result"]["file_path"]
        self.url = agent.url.format(token=agent.token, method=file_path)
        self.raw = data

    async def a_parser(self, agent: TelegramAgent, data: dict):
        file_path = await agent.a_get_file(data["file_id"])["result"]["file_path"]
        self.url = agent.url.format(token=agent.token, method=file_path)
        self.raw = data


class TelegramMessage(Message):
    def parser(self, agent: TelegramAgent, data: dict):
        self.text = data.get("text", None)
        for photo_data in data.get("photo", []):
            photo = TelegramPhotoSize()
            photo.parser(agent, photo_data)
            self.images.append(photo)
        if "audio" in data:
            audio = TelegramAudio()
            audio.parser(agent, data["audio"])
            self.audios.append(audio)
        if "video" in data:
            video = TelegramVideo()
            video.parser(agent, data["video"])
            self.videos.append(video)
        if "document" in data:
            document = TelegramDocument()
            document.parser(agent, data["document"])
            self.documents.append(document)
        if "location" in data:
            location = TelegramLocation(data["location"])
            self.locations.append(location)
        self.raw = data

    async def a_parser(self, agent: TelegramAgent, data: dict):
        self.text = data.get("text")
        for photo_data in data.get("photo", []):
            photo = TelegramPhotoSize()
            await photo.a_parser(agent, photo_data)
            self.images.append(photo)
        if "audio" in data:
            audio = TelegramAudio()
            await audio.a_parser(agent, data["audio"])
            self.audios.append(audio)
        if "video" in data:
            video = TelegramVideo()
            await video.a_parser(agent, data["video"])
            self.videos.append(video)
        if "document" in data:
            document = TelegramDocument()
            await document.a_parser(agent, data["document"])
            self.documents.append(document)
        if "location" in data:
            location = TelegramLocation(data["location"])
            self.locations.append(location)
        self.raw = data


class TelegramAudio(Audio, TelegramAttachment):
    pass


class TelegramDocument(Document, TelegramAttachment):
    pass


class TelegramPhotoSize(Image, TelegramAttachment):
    pass


class TelegramVideo(Video, TelegramAttachment):
    pass


class TelegramLocation(Location):
    def __init__(self, data: dict):
        super().__init__(data["longitude"], data["latitiude"])
        self.raw = data
