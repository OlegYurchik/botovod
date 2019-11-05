from __future__ import annotations
from .agents import Agent, Attachment, Chat, Keyboard, KeyboardButton, Location, Message
import aiofiles
import aiohttp
import asyncio
from datetime import datetime
import json
import io
import logging
import requests
from threading import Thread
from typing import Any, Dict, Iterator, List, Optional, Tuple
import time


class TelegramAgent(Agent):
    WEBHOOK = "webhook"
    POLLING = "polling"

    BASE_URL = "https://api.telegram.org/bot{token}/{method}"
    FILE_URL = "https://api.telegram.org/file/bot{token}/{file_path}"

    def __init__(self, token: str, method: str=POLLING, delay: int=5,
                 webhook_url: Optional[str]=None, certificate_path: Optional[str]=None,
                 logger: Optional[logging.Logger]=None):

        super().__init__(logger=logger)
        self.token = token
        self.method = method

        if method == self.POLLING:
            self.delay = delay
            self.thread = None
        elif webhook_url is None:
            raise ValueError("Need set webhook_url")
        else:
            self.webhook_url = webhook_url
            self.certificate_path = certificate_path

        self.last_update = 0

    def start(self):

        if self.logger:
            self.logger.info("[%s:%s] Starting agent...", self, self.name)

        self.set_webhook()
        self.running = True

        if self.method == self.POLLING:
            if self.thread and self.thread.is_alive():
                self.thread.join()
            self.thread = Thread(target=self.polling, daemon=True)
            self.thread.start()
            log_message = "[%s:%s] Started by polling."
        elif self.method == self.WEBHOOK:
            log_message = "[%s:%s] Started by webhook."

        if self.logger:
            self.logger.info(log_message, self, self.name)

    async def a_start(self):

        if self.logger:
            self.logger.info("[%s:%s] Starting agent...", self, self.name)

        await self.a_set_webhook()
        self.running = True

        if self.method == self.POLLING:
            asyncio.create_task(self.a_polling())
            log_message = "[%s:%s] Started by polling."
        elif self.method == self.WEBHOOK:
            log_message = "[%s:%s] Started by webhook."

        if self.logger:
            self.logger.info(log_message, self, self.name)

    def stop(self):

        if self.logger:
            self.logger.info("[%s:%s] Stopping agent...", self, self.name)

        if self.method == self.POLLING:
            self.thread.join()
            self.thread = None
        self.running = False

        if self.logger:
            self.logger.info("[%s:%s] Agent stopped.", self, self.name)

    async def a_stop(self):

        if self.logger:
            self.logger.info("[%s:%s] Stopping agent...", self, self.name)

        self.running = False

        if self.logger:
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
                if self.logger:
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
                if self.logger:
                    self.logger.exception("[%s:%s] Got exception")
                    self.logger.error("[%s:%s] Get incorrect update! Code: %s. Response: %s", self,
                                      self.name, response.status, await response.text())
            finally:
                await asyncio.sleep(self.delay)

    def set_webhook(self):

        if self.logger:
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
            if self.logger:
                self.logger.error("[%s:%s] Webhook doesn't set! Code: %s; Body: %s", self,
                                  self.name, response.status_code, response.text)
            return

        if self.logger:
            self.logger.info("[%s:%s] Set webhook.", self, self.name)

    async def a_set_webhook(self):

        if self.logger:
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
            if self.logger:
                self.logger.error("[%s:%s] Webhook doesn't set! Code: %s; Body: %s", self,
                                  self.name, response.status, response.text)
            return

        if self.logger:
            self.logger.info("[%s:%s] Set webhook.", self, self.name)
            self.logger.info("RESPONSE: %s", await response.text())

    def send_message(self, chat: Chat, text: Optional[str]=None, images: Iterator[Attachment]=(),
                     audios: Iterator[Attachment]=(), documents: Iterator[Attachment]=(),
                     videos: Iterator[Attachment]=(), locations: Iterator[Location]=(),
                     keyboard: Optional[Keyboard]=None, html: bool=False, markdown: bool=False,
                     web_preview: bool=True, notification: bool=True,
                     reply: Optional[Message]=None, remove_keyboard: bool=False):

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
            elif remove_keyboard:
                data["reply_markup"] = '{"remove_keyboard": true}'
            if html:
                data["parse_mode"] = "HTML"
            elif markdown:
                data["parse_mode"] = "Markdown"
            if reply is not None:
                data["reply_to_message_id"] = reply.id
            response = requests.post(url, data=data)
            if response.status_code != 200:
                if self.logger:
                    self.logger.error("[%s:%s] Cannot send message! Code: %s; Body: %s", self,
                                      self.name, response.status_code, response.text)
            else:
                messages.append(TelegramMessage.parse(response.json()["result"]))
        for image in images:
            message = self.send_photo(chat, image, keyboard=keyboard,
                                      remove_keyboard=remove_keyboard)
            if message is not None:
                messages.append(message)
        for audio in audios:
            message = self.send_audio(chat, audio, keyboard=keyboard,
                                       remove_keyboard=remove_keyboard)
            if message is not None:
                messages.append(message)
        for document in documents:
            message = self.send_document(chat, document, keyboard=keyboard,
                                         remove_keyboard=remove_keyboard)
            if message is not None:
                messages.append(message)
        for video in videos:
            message = self.send_video(chat, video, keyboard=keyboard,
                                      remove_keyboard=remove_keyboard)
            if message is not None:
                messages.append(message)
        for location in locations:
            message = self.send_location(chat, location, keyboard=keyboard,
                                         remove_keyboard=remove_keyboard)
            if message is not None:
                messages.append(message)
        return messages

    async def a_send_message(self, chat: Chat, text: Optional[str]=None,
                             images: Iterator[Attachment]=(), audios: Iterator[Attachment]=(),
                             documents: Iterator[Attachment]=(), videos: Iterator[Attachment]=(),
                             locations: Iterator[Location]=(), keyboard: Optional[Keyboard]=None,
                             html: bool=False, markdown: bool=False, web_preview: bool=True,
                             notification: bool=True, reply: Optional[Message]=None,
                             remove_keyboard: bool=False):

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
            elif remove_keyboard:
                data["reply_markup"] = '{"remove_keyboard": true}'
            if html:
                data["parse_mode"] = "HTML"
            elif markdown:
                data["parse_mode"] = "Markdown"
            if reply is not None:
                data["reply_to_message_id"] = reply.id
            async with aiohttp.ClientSession() as session:
                response = await session.post(url, data=data)
            if response.status != 200:
                if self.logger:
                    self.logger.error("[%s:%s] Cannot send message! Code: %s; Body: %s", self,
                                      self.name, response.status, await response.text())
            else:
                messages.append(TelegramMessage.parse((await response.json())["result"]))
        for image in images:
            message = await self.a_send_photo(chat, image, keyboard=keyboard,
                                              remove_keyboard=remove_keyboard)
            if message is not None:
                messages.append(message)
        for audio in  audios:
            message = await self.a_send_audio(chat, audio, keyboard=keyboard,
                                              remove_keyboard=remove_keyboard)
            if message is not None:
                messages.append(message)
        for document in documents:
            message = await self.a_send_document(chat, document, keyboard=keyboard,
                                                 remove_keyboard=remove_keyboard)
            if message is not None:
                messages.append(message)
        for video in videos:
            message = await self.a_send_video(chat, video, keyboard=keyboard,
                                              remove_keyboard=remove_keyboard)
            if message is not None:
                messages.append(message)
        for location in locations:
            message = await self.a_send_location(chat, location, keyboard=keyboard,
                                                 remove_keyboard=remove_keyboard)
            if message is not None:
                messages.append(message)
        return messages

    def send_attachment(self, type: str, chat: Chat, attachment: Attachment,
                        keyboard: Optional[Keyboard]=None, remove_keyboard: bool=False):

        url = self.BASE_URL.format(token=self.token, method="send" + type.capitalize())
        attachment_data = TelegramAttachment.render(attachment)

        data = {"chat_id": chat.id}
        files = {}
        if isinstance(attachment_data, io.IOBase):
            files = {type: attachment_data}
        else:
            data[type] = attachment_data

        if keyboard is not None:
            if hasattr(keyboard, "render"):
                data["reply_markup"] = keyboard.render()
            else:
                data["reply_markup"] = TelegramKeyboard.default_render(keyboard)
        elif remove_keyboard:
            data["reply_markup"] = '{"remove_keyboard": true}'

        response = requests.post(url, data=data, files=files)

        if response.status_code != 200:
            if self.logger:
                self.logger.error("[%s:%s] Cannot send %s! Code: %s; Body: %s", self, self.name,
                                  type, response.status_code, response.text)
        else:
            return TelegramMessage.parse(response.json()["result"])

    async def a_send_attachment(self, type: str, chat: Chat, attachment: Attachment,
                                keyboard: Optional[Keyboard]=None, remove_keyboard: bool=False):

        url = self.BASE_URL.format(token=self.token, method="send" + type.capitalize())
        attachment_data = await TelegramAttachment.a_render(attachment)

        data = {"chat_id": chat.id, type: attachment_data}

        if keyboard is not None:
            if hasattr(keyboard, "render"):
                data["reply_markup"] = keyboard.render()
            else:
                data["reply_markup"] = TelegramKeyboard.default_render(keyboard)
        elif remove_keyboard:
            data["reply_markup"] = '{"remove_keyboard": true}'

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as response:
                return response
        if response.status != 200:
            if self.logger:
                self.logger.error("[%s:%s] Cannot send %s! Code: %s; Body: %s", self, self.name,
                                  type, response.status, await response.text())
        else:
            return await TelegramMessage.a_parse((await response.json())["result"])

    def send_photo(self, chat: Chat, image: Attachment, keyboard: Optional[Keyboard]=None,
                   remove_keyboard: bool=False):

        return self.send_attachment(
            type="photo",
            chat=chat,
            attachment=image,
            keyboard=keyboard,
            remove_keyboard=remove_keyboard,
        )

    async def a_send_photo(self, chat: Chat, image: Attachment, keyboard: Optional[Keyboard]=None,
                           remove_keyboard: bool=False):

        return await self.a_send_attachment(
            type="photo",
            chat=chat,
            attachment=image,
            keyboard=keyboard,
            remove_keyboard=remove_keyboard,
        )

    def send_audio(self, chat: Chat, audio: Attachment, keyboard: Optional[Keyboard]=None,
                   remove_keyboard: bool=False):

        return self.send_attachment(
            type="audio",
            chat=chat,
            attachment=audio,
            keyboard=keyboard,
            remove_keyboard=remove_keyboard,
        )

    async def a_send_audio(self, chat: Chat, audio: Attachment, keyboard: Optional[Keyboard]=None,
                           remove_keyboard: bool=False):

        return await self.a_send_attachment(
            type="audio",
            chat=chat,
            attachment=audio,
            keyboard=keyboard,
            remove_keyboard=remove_keyboard,
        )

    def send_document(self, chat: Chat, document: Attachment, keyboard: Optional[Keyboard]=None,
                      remove_keyboard: bool=False):

        return self.send_attachment(
            type="document",
            chat=chat,
            attachment=document,
            keyboard=keyboard,
            remove_keyboard=remove_keyboard,
        )

    async def a_send_document(self, chat: Chat, document: Attachment,
                              keyboard: Optional[Keyboard]=None, remove_keyboard: bool=False):

        return await self.a_send_attachment(
            type="document",
            chat=chat,
            attachment=document,
            keyboard=keyboard,
            remove_keyboard=remove_keyboard,
        )

    def send_video(self, chat: Chat, video: Attachment, keyboard: Optional[Keyboard]=None,
                   remove_keyboard: bool=False):

        return self.send_attachment(
            type="video",
            chat=chat,
            attachment=video,
            keyboard=keyboard,
            remove_keyboard=remove_keyboard,
        )

    async def a_send_video(self, chat: Chat, video: Attachment, keyboard: Optional[Keyboard]=None,
                           remove_keyboard: bool=False):

        return await self.a_send_attachment(
            type="video",
            chat=chat,
            attachment=video,
            keyboard=keyboard,
            remove_keyboard=remove_keyboard,
        )

    def send_location(self, chat: Chat, location: Location, keyboard: Optional[Keyboard]=None,
                      remove_keyboard: bool=True):

        url = self.BASE_URL.format(token=self.token, method="sendLocation")
        data = {"chat_id": chat.id, "longitude": location.longitude, "latitude": location.latitude}
        if keyboard is not None:
            if hasattr(keyboard, "render"):
                data["reply_markup"] = keyboard.render()
            else:
                data["reply_markup"] = TelegramKeyboard.default_render(keyboard)
        elif remove_keyboard:
            data["reply_markup"] = '{"remove_keyboard": true}'
        response = requests.post(url, data=data)
        if response.status_code != 200:
            if self.logger:
                self.logger.error("[%s:%s] Cannot send location! Code: %s; Body: %s", self,
                                  self.name, response.status_code, response.text)
        else:
            return TelegramMessage.parse(response.json())

    async def a_send_location(self, chat: Chat, location: Location,
                              keyboard: Optional[Keyboard]=None, remove_keyboard: bool=False):

        url = self.BASE_URL.format(token=self.token, method="sendLocation")
        data = {"chat_id": chat.id, "longitude": location.longitude, "latitude": location.latitude}
        if keyboard is not None:
            if hasattr(keyboard, "render"):
                data["reply_markup"] = keyboard.render()
            else:
                data["reply_markup"] = TelegramKeyboard.default_render(keyboard)
        elif remove_keyboard:
            data["reply_markup"] = '{"remove_keyboard": true}'
        async with aiohttp.ClientSession() as session:
            response = await session.post(url, data=data)
        if response.status != 200:
            if self.logger:
                self.logger.error("[%s:%s] Cannot send location! Code: %s; Body: %s", self,
                                  self.name, response.status, await response.text())
        else:
            return await TelegramMessage.a_parse((await response.json())["result"])

    def get_file(self, file_id: int):

        url = self.BASE_URL.format(token=self.token, method="getFile")
        response = requests.get(url, params={"file_id": file_id})
        if response.status_code != 200:
            if self.logger:
                self.logger.error("[%s:%s] Cannot get file! Code: %s; Body: %s", self, self.name,
                                  response.status_code, response.text)
        return TelegramAttachment.parse(response.json()["result"], agent=self)

    async def a_get_file(self, file_id: int):

        url = self.BASE_URL.format(token=self.token, method="getFile")
        async with aiohttp.ClientSession() as session:
            response = await session.get(url, params={"file_id": file_id})
        if response.status != 200:
            if self.logger:
                self.logger.error("[%s:%s] Cannot get file! Code: %s; Body: %s", self, self.name,
                                  response.status, await response.text())
        return await TelegramAttachment.a_parse((await response.json())["result"], agent=self)

    def edit_message_text(self, chat: Chat, message: TelegramMessage, text: str,
                          keyboard: Optional[TelegramInlineKeyboard]=None, html: bool=False,
                          markdown: bool=False, web_preview: bool=True):

        url = self.BASE_URL.format(token=self.token, method="editMessageText")
        data = {
            "chat_id": chat.id,
            "message_id": message.raw["id"],
            "text": text,
            "disable_web_page_preview": not web_preview,
        }
        if keyboard is not None:
            data["reply_markup"] = keyboard.render()
        if html:
            data["parse_mode"] = "HTML"
        elif markdown:
            data["parse_mode"] = "Markdown"
        response = requests.post(url, data=data)
        if response.status_code != 200:
            if self.logger:
                self.logger.error("[%s:%s] Cannot edit message text! Code: %s; Body: %s", self,
                                  self.name, response.status_code, response.text)

    async def a_edit_message_text(self, chat: Chat, message: TelegramMessage, text: str,
                                  keyboard: Optional[TelegramInlineKeyboard]=None, html: bool=False,
                                  markdown: bool=False, web_preview: bool=True):

        url = self.BASE_URL.format(token=self.token, method="editMessageText")
        data = {
            "chat_id": chat.id,
            "message_id": message.raw["id"],
            "text": text,
            "disable_web_page_preview": not web_preview,
        }
        if keyboard is not None:
            data["reply_markup"] = keyboard.render()
        if html:
            data["parse_mode"] = "HTML"
        elif markdown:
            data["parse_mode"] = "Markdown"
        async with aiohttp.ClientSession() as session:
            response = await session.post(url, data=data)
        if response.status != 200:
            if self.logger:
                self.logger.error("[%s:%s] Cannot edit message text! Code: %s; Body: %s", self,
                                  self.name, response.status, await response.text())

    def edit_message_caption(self, chat: Chat, message: TelegramMessage, caption: str,
                             keyboard: Optional[TelegramInlineKeyboard]=None, html: bool=False,
                             markdown: bool=False):

        url = self.BASE_URL.format(token=self.token, method="editMessageCaption")
        data = {"chat_id": chat.id, "message_id": message.raw["id"], "caption": caption}
        if keyboard is not None:
            data["reply_markup"] = keyboard.render()
        if html:
            data["parse_mode"] = "HTML"
        elif markdown:
            data["parse_mode"] = "Markdown"
        response = requests.post(url, data=data)
        if response.status_code != 200:
            if self.logger:
                self.logger.error("[%s:%s] Cannot edit message caption! Code: %s; Body: %s", self,
                                  self.name, response.status_code, response.text)

    async def a_edit_message_caption(self, chat: Chat, message: TelegramMessage, caption: str,
                                     keyboard: Optional[TelegramInlineKeyboard]=None,
                                     html: bool=False, markdown: bool=False):

        url = self.BASE_URL.format(token=self.token, method="editMessageCaption")
        data = {"chat_id": chat.id, "message_id": message.raw["id"], "caption": caption}
        if keyboard is not None:
            data["reply_markup"] = keyboard.render()
        if html:
            data["parse_mode"] = "HTML"
        elif markdown:
            data["parse_mode"] = "Markdown"
        async with aiohttp.ClientSession() as session:
            response = await session.post(url, data=data)
        if response.status != 200:
            if self.logger:
                self.logger.error("[%s:%s] Cannot edit message caption! Code: %s; Body: %s", self,
                                  self.name, response.status, await response.text())

    def edit_message_media(self, chat: Chat, message: TelegramMessage, media: Attachment, type: str,
                           thumb: Optional[Attachment]=None, caption: Optional[str]=None,
                           markdown: bool=False, html: bool=False,
                           keyboard: Optional[TelegramInlineKeyboard]=None, **raw):

        url = self.BASE_URL.format(token=self.token, method="editMessageMedia")
        attachment_data = TelegramAttachment.render(media)
        thumb_data = TelegramAttachment(thumb) if thumb else None

        data = {"chat_id": chat.id, "message_id": message.id}
        media_data = {"type": type}
        files = {}
        if isinstance(attachment_data, io.IOBase):
            files["media"] = attachment_data
        else:
            media_data["media"] = attachment_data
        if isinstance(attachment_data, io.IOBase):
            files["thumb"] = thumb_data
        else:
            media_data["thumb"] = thumb_data

        if caption is not None:
            media_data["caption"] = caption
        if markdown:
            media_data["parse_mode"] = "Markdown"
        elif html:
            media_data["parse_mode"] = "HTML"
        media_data.update(raw)
        if keyboard is not None:
            data["reply_markup"] = keyboard.render()
        data["media"] = json.dumps(media_data)

        response = requests.post(url=url, data=data, files=files)

        if response.status_code != 200:
            if self.logger:
                self.logger.error("[%s:%s] Cannot edit message media! Code: %s; Body: %s", self,
                                  self.name, response.status_code, response.text)

    async def a_edit_message_media(self, chat: Chat, message: TelegramMessage, media: Attachment,
                                   type: str, thumb: Optional[Attachment]=None,
                                   caption: Optional[str]=None, markdown: bool=False,
                                   html: bool=False,
                                   keyboard: Optional[TelegramInlineKeyboard]=None, **raw):

        url = self.BASE_URL.format(token=self.token, method="editMessageMedia")
        attachment_data = TelegramAttachment.a_render(media)
        thumb_data = TelegramAttachment.a_render(thumb) if thumb else None

        data = {"chat_id": chat.id, "message_id": message.id}
        media_data = {"type": type, "media": attachment_data}
        if isinstance(thumb_data, io.IOBase):
            data["thumb"] = thumb_data
        else:
            media_data["thumb"] = thumb_data
        if caption:
            media_data["caption"] = caption
        if markdown:
            media_data["parse_mode"] = "Markdown"
        elif html:
            media_data["parse_mode"] = "HTML"
        media_data.update(raw)
        if keyboard:
            data["reply_markup"] = keyboard.render()
        data["media"] = json.dumps(media_data)
        async with aiohttp.ClientSession() as session:
            response = await session.post(url, data=data)
        if response.status != 200:
            if self.logger:
                self.logger.error("[%s:%s] Cannot edit message %s! Code: %s; Body: %s", self,
                                  self.name, type, response.status, await response.text())

    def edit_message_image(self, chat: Chat, message: TelegramMessage, image: Attachment,
                           caption: Optional[str]=None, markdown: bool=False, html: bool=False,
                           keyboard: Optional[TelegramInlineKeyboard]=None):

        return self.edit_message_media(chat=chat, message=message, media=image, type="photo",
                                       caption=caption, markdown=markdown, html=html,
                                       keyboard=keyboard)

    async def a_edit_message_image(self, chat: Chat, message: TelegramMessage, image: Attachment,
                                   caption: Optional[str]=None, markdown: bool=False,
                                   html: bool=False,
                                   keyboard: Optional[TelegramInlineKeyboard]=None):

        return await self.a_edit_message_media(chat=chat, message=message, media=image,
                                               type="photo", caption=caption, markdown=markdown,
                                               html=html, keyboard=keyboard)

    def edit_message_video(self, chat: Chat, message: TelegramMessage, video: Attachment,
                           thumb: Optional[Attachment]=None, caption: Optional[str]=None,
                           markdown: bool=False, html: bool=False, width: Optional[int]=None,
                           height: Optional[int]=None, duration: Optional[int]=None,
                           supports_streaming: Optional[bool]=None,
                           keyboard: Optional[TelegramInlineKeyboard]=None):

        data = {}
        if width:
            data["width"] = width
        if height:
            data["height"] = height
        if duration:
            data["duration"] = duration
        if supports_streaming:
            data["supports_streaming"] = supports_streaming
        return self.edit_message_media(chat=chat, message=message, media=video, type="video",
                                       thumb=thumb, caption=caption, markdown=markdown, html=html,
                                       keyboard=keyboard, **data)

    async def a_edit_message_video(self, chat: Chat, message: TelegramMessage, video: Attachment,
                                   thumb: Optional[Attachment]=None, caption: Optional[str]=None,
                                   markdown: bool=False, html: bool=False,
                                   width: Optional[int]=None, height: Optional[int]=None,
                                   duration: Optional[int]=None,
                                   supports_streaming: Optional[bool]=None,
                                   keyboard: Optional[TelegramInlineKeyboard]=None):

        data = {}
        if width:
            data["width"] = width
        if height:
            data["height"] = height
        if duration:
            data["duration"] = duration
        if supports_streaming:
            data["supports_streaming"] = supports_streaming
        return await self.a_edit_message_media(chat=chat, message=message, media=video,
                                               type="video", thumb=thumb, caption=caption,
                                               markdown=markdown, html=html, keyboard=keyboard,
                                               **data)

    def edit_message_animation(self, chat: Chat, message: TelegramMessage, animation: Attachment,
                               thumb: Optional[Attachment]=None, caption: Optional[str]=None,
                               markdown: bool=False, html: bool=False, width: Optional[int]=None,
                               height: Optional[int]=None, duration: Optional[int]=None,
                               keyboard: Optional[TelegramInlineKeyboard]=None):

        data = {}
        if width is not None:
            data["width"] = width
        if height is not None:
            data["height"] = height
        if duration is not None:
            data["duration"] = duration
        return self.edit_message_media(chat=chat, message=message, media=animation,
                                       type="animation", thumb=thumb, caption=caption,
                                       markdown=markdown, html=html, keyboard=keyboard, **data)

    async def a_edit_message_animation(self, chat: Chat, message: TelegramMessage,
                                       animation: Attachment, thumb: Optional[Attachment]=None,
                                       caption: Optional[str]=None, markdown: bool=False,
                                       html: bool=False, width: Optional[int]=None,
                                       height: Optional[int]=None, duration: Optional[int]=None,
                                       keyboard: Optional[TelegramInlineKeyboard]=None):

        data = {}
        if width is not None:
            data["width"] = width
        if height is not None:
            data["height"] = height
        if duration is not None:
            data["duration"] = duration
        return await self.a_edit_message_media(chat=chat, message=message, media=animation,
                                               type="animation", thumb=thumb, caption=caption,
                                               markdown=markdown, html=html, keyboard=keyboard,
                                               **data)

    def edit_message_audio(self, chat: Chat, message: TelegramMessage, audio: Attachment,
                           thumb: Optional[Attachment]=None, caption: Optional[str]=None,
                           markdown: bool=False, html: bool=False, duration: Optional[int]=None,
                           performer: Optional[str]=None, title: Optional[str]=None,
                           keyboard: Optional[TelegramInlineKeyboard]=None):

        data = {}
        if duration is not None:
            data["duration"] = duration
        if performer is not None:
            data["performer"] = performer
        if title is not None:
            data["title"] = title
        return self.edit_message_media(chat=chat, message=message, media=audio, type="audio",
                                       thumb=thumb, caption=caption, markdown=markdown, html=html,
                                       keyboard=keyboard, **data)

    async def a_edit_message_audio(self, chat: Chat, message: TelegramMessage,
                                   audio: Attachment, thumb: Optional[Attachment]=None,
                                   caption: Optional[str]=None, markdown: bool=False,
                                   html: bool=False, duration: Optional[int]=None,
                                   performer: Optional[str]=None, title: Optional[str]=None,
                                   keyboard: Optional[TelegramInlineKeyboard]=None):

        data = {}
        if duration is not None:
            data["duration"] = duration
        if performer is not None:
            data["performer"] = performer
        if title is not None:
            data["title"] = title
        return await self.a_edit_message_media(chat=chat, message=message, media=audio,
                                               type="audio", thumb=thumb, caption=caption,
                                               markdown=markdown, html=html, keyboard=keyboard,
                                               **data)

    def edit_message_document(self, chat: Chat, message: TelegramMessage, document: Attachment,
                              thumb: Optional[Attachment]=None, caption: Optional[str]=None,
                              markdown: bool=False, html: bool=False,
                              keyboard: Optional[TelegramInlineKeyboard]=None):

        return self.edit_message_media(chat=chat, message=message, media=document, type="document",
                                       thumb=thumb, caption=caption, markdown=markdown, html=html,
                                       keyboard=keyboard)

    async def a_edit_message_document(self, chat: Chat, message: TelegramMessage,
                                      document: Attachment, thumb: Optional[Attachment]=None,
                                      caption: Optional[str]=None, markdown: bool=False,
                                      html: bool=False,
                                      keyboard: Optional[TelegramInlineKeyboard]=None):

        return await self.a_edit_message_media(chat=chat, message=message, media=document,
                                               type="document", thumb=thumb, caption=caption,
                                               markdown=markdown, html=html, keyboard=keyboard)

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
            if self.logger:
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
            if self.logger:
                self.logger.error("[%s:%s] Cannot edit message keyboard! Code: %s; Body: %s", self,
                                  self.name, response.status, await response.text())

    def delete_message(self, chat: Chat, message: TelegramMessage):

        url = self.BASE_URL.format(token=self.token, method="deleteMessage")
        data = {"chat_id": chat.id, "message_id": message.raw["id"]}
        response = requests.post(url, data=data)
        if response.status_code != 200:
            if self.logger:
                self.logger.error("[%s:%s] Cannot delete message! Code: %s; Body: %s", self,
                                  self.name, response.status_code, response.text)

    async def a_delete_message(self, chat: Chat, message: TelegramMessage):

        url = self.BASE_URL.format(token=self.token, method="deleteMessage")
        data = {"chat_id": chat.id, "message_id": message.raw["id"]}
        async with aiohttp.ClientSession() as session:
            response = await session.post(url, data=data)
        if response.status != 200:
            if self.logger:
                self.logger.error("[%s:%s] Cannot delete message! Code: %s; Body: %s", self,
                                  self.name, response.status, await response.text())

    def send_chat_action(self, chat: Chat, action: str):

        url = self.BASE_URL.format(token=self.token, method="sendChatAction")
        data = {"chat_id": chat.id, "action": action}
        response = requests.post(url, data=data)
        if response.status_code != 200:
            if self.logger:
                self.logger.error("[%s:%s] Cannot send chat action! Code: %s; Body: %s", self,
                                  self.name, response.status_code, response.text)

    async def a_send_chat_action(self, chat: Chat, action: str):

        url = self.BASE_URL.format(token=self.token, method="sendChatAction")
        data = {"chat_id": chat.id, "action": action}
        async with aiohttp.ClientSession() as session:
            response = await session.post(url, data=data)
        if response.status != 200:
            if self.logger:
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
                 last_name: Optional[str]=None, username: Optional[str]=None,
                 language: Optional[str]=None):

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
    def is_bot(self, value: bool):

        self.raw["is_bot"] = value

    @property
    def first_name(self) -> str:

        return self.raw["first_name"]

    @first_name.setter
    def first_name(self, value: str):

        self.raw["first_name"] = value

    @property
    def last_name(self) -> Optional[str]:

        return self.raw.get("last_name")

    @last_name.setter
    def last_name(self, value: Optional[str]):

        if value is not None:
            self.raw["last_name"] = value
        elif "last_name" in self.raw:
            del self.raw["last_name"]

    @property
    def username(self) -> Optional[str]:

        return self.raw.get("username")

    @username.setter
    def username(self, value: Optional[str]):

        if value is not None:
            self.raw["username"] = value
        elif "username" in self.raw:
            del self.raw["username"]

    @property
    def language(self) -> Optional[str]:

        return self.raw.get("langugage")

    @language.setter
    def language(self, value: Optional[str]):

        if value is not None:
            self.raw["language"] = value
        elif "language" in self.raw:
            del self.raw["language"]


class TelegramChat(Chat):
    def __init__(self, agent: TelegramAgent, id: int, type: str, title: Optional[str]=None,
                 username: Optional[str]=None, first_name: Optional[str]=None,
                 last_name: Optional[str]=None, photo: Optional[dict]=None,
                 description: Optional[str]=None, invite_link: Optional[str]=None,
                 pinned_message: Optional[dict]=None, permissions: Optional[dict]=None,
                 sticker_set: Optional[str]=None, can_set_sticker: Optional[bool]=None):

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
    def type(self, value: str):

        self.raw["type"] = value

    @property
    def title(self) -> Optional[str]:

        return self.raw.get("title")

    @title.setter
    def title(self, value: Optional[str]):

        if value is not None:
            self.raw["title"] = value
        elif "title" in self.raw:
            del self.raw["title"]

    @property
    def username(self) -> Optional[str]:

        return self.raw.get("username")

    @username.setter
    def username(self, value: Optional[str]):

        if value is not None:
            self.raw["username"] = value
        elif "username" in self.raw:
            del self.raw["username"]

    @property
    def first_name(self) -> Optional[str]:

        return self.raw.get("first_name")

    @first_name.setter
    def first_name(self, value: Optional[str]):

        if value is not None:
            self.raw["first_name"] = value
        elif "first_name" in self.raw:
            del self.raw["first_name"]

    @property
    def last_name(self) -> Optional[str]:

        return self.raw.get("last_name")

    @last_name.setter
    def last_name(self, value: Optional[str]):

        if value is not None:
            self.raw["last_name"] = value
        elif "last_name" in self.raw:
            del self.raw["last_name"]

    @property
    def photo(self) -> Optional[str]:

        return self.raw["photo"]

    @photo.setter
    def photo(self, value: Optional[dict]):

        if value is not None:
            self.raw["photo"] = value
        elif "photo" in self.raw:
            del self.raw["photo"]

    @property
    def description(self) -> Optional[str]:

        return self.raw.get("description")

    @description.setter
    def description(self, value: Optional[str]):

        if value is not None:
            self.raw["description"] = value
        elif "description" in self.raw:
            del self.raw["description"]

    @property
    def invite_link(self) -> Optional[str]:

        return self.raw.get("invite_link")

    @invite_link.setter
    def invite_link(self, value: Optional[str]):

        if value is not None:
            self.raw["invite_link"] = value
        elif "invite_link" in self.raw:
            del self.raw["invite_link"]

    @property
    def pinned_message(self) -> Optional[TelegramMessage]:

        if "pinned_message" in self.raw:
            return TelegramMessage.parse(data=self.raw["pinned_message"])

    @pinned_message.setter
    def pinned_message(self, value: Optional[TelegramMessage]):

        if value is not None:
            self.raw["pinned_message"] = value.render()
        elif "pinned_message" in self.raw:
            del self.raw["pinned_message"]

    @property
    def permissions(self) -> Optional[dict]:

        return self.raw.get("permissions")

    @permissions.setter
    def permissions(self, value: Optional[dict]):

        if value is not None:
            self.raw["permissions"] = value
        elif "permissions" in self.raw:
            del self.raw["permissons"]

    @property
    def sticker_set(self) -> Optional[str]:

        return self.raw.get("sticker_set")

    @sticker_set.setter
    def sticker_set(self, value: Optional[str]):

        if value is not None:
            self.raw["sticker_set"] = value
        elif "sticker_set" in self.raw:
            del self.raw["sticker_set"]

    @property
    def can_set_sticker(self) -> Optional[bool]:

        return self.raw.get("can_set_sticker")

    @can_set_sticker.setter
    def can_set_sticker(self, value: Optional[bool]):

        if value is not None:
            self.raw["can_set_sticker"] = value
        elif "can_set_sticker" in self.raw:
            del self.raw["can_set_sticker"]


# Нужны остальные необязательные поля
class TelegramMessage(Message):
    def __init__(self, id: int, datetime: int, chat: dict, text: Optional[str]=None,
                 images: Iterator[Attachment]=(), audios: Iterator[Attachment]=(),
                 videos: Iterator[Attachment]=(), documents: Iterator[Attachment]=(),
                 locations: Iterator[Location]=(), **raw):

        super().__init__(id=id, datetime=datetime, chat=chat, text=text, images=images,
                         audios=audios, videos=videos, documents=documents, locations=locations,
                         **raw)

    @classmethod
    def parse(cls, data: dict, agent: Optional[TelegramAgent]=None):

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
        raw = {"contact": data.get("contact")}
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
            **raw,
        )

    @classmethod
    async def a_parse(cls, data: dict, agent: Optional[TelegramAgent]=None):

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
        raw = {"contact": data.get("contact")}
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
            **raw,
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
    def id(self, value: int):

        self.raw["id"] = value

    @property
    def datetime(self) -> datetime:

        return datetime.utcfromtimestamp(self.raw["datetime"])

    @datetime.setter
    def datetime(self, value: datetime):

        self.raw["datetime"] = datetime.timestamp()

    @property
    def chat(self) -> Chat:

        return TelegramChat.parse(agent=None, data=self.raw["chat"])

    @chat.setter
    def chat(self, value: TelegramChat):

        self.raw["chat"] = value.render()

    @property
    def contact(self):

        if "contact" in self.raw:
            return TelegramContact.parse(self.raw["contact"])
        else:
            return None

    @contact.setter
    def contact(self, value: Optional[TelegramContact]=None):

        if value is not None:
            self.raw["contact"] = value.render()
        elif "contact" in self.raw:
            del self.raw["contact"]


class TelegramCallback(Message):
    def __init__(self, id: str, user: dict, message: Optional[dict]=None,
                 inline_message_id: Optional[str]=None, chat_instance: Optional[str]=None,
                 data: Optional[str]=None, game_short_name: Optional[str]=None):

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
    def message(self) -> Optional[TelegramMessage]:

        if "message" in self.raw:
            return TelegramMessage.parse(data=self.raw["message"])
        else:
            return None

    @message.setter
    def message_setter(self, value: Optional[TelegramMessage]):

        if value is not None:
            self.raw["message"] = value.render()
        elif "message" in self.raw:
            del self.raw["message"]

    @property
    def inline_message_id(self) -> Optional[str]:

        return self.raw.get("inline_message_id")

    @inline_message_id.setter
    def inline_message_id_setter(self, value: Optional[str]):

        if value is not None:
            self.raw["inline_message_id"] = value
        elif "inline_message_id" in self.raw:
            del self.raw["inline_message_id"]

    @property
    def chat_instance(self) -> Optional[str]:

        return self.raw.get("chat_instance")

    @chat_instance.setter
    def chat_instance_setter(self, value: Optional[str]):

        if value is not None:
            self.raw["chat_instance"] = value
        elif "chat_instance" in self.raw:
            del self.raw["chat_instance"]

    @property
    def data(self) -> Optional[str]:

        return self.raw.get("data")

    @data.setter
    def data_setter(self, value: Optional[str]):

        if value is not None:
            self.raw["data"] = value
        elif "data" in self.raw:
            del self.raw["data"]

    @property
    def game_short_name(self) -> Optional[str]:

        return self.raw.get("game_short_name")

    @game_short_name.setter
    def game_short_name_setter(self, value: Optional[str]):

        if value is not None:
            self.raw["game_short_name"] = value
        elif "game_short_name" in self.raw:
            del self.raw["game_short_name"]


class TelegramAttachment(Attachment):
    def __init__(self, url: Optional[str]=None, filepath: Optional[str]=None,
                 id: Optional[str]=None, size: Optional[int]=None):

        super().__init__(url=url, filepath=filepath, id=id, size=size)

    @classmethod
    def parse(cls, data: dict, agent: Optional[TelegramAgent]=None):

        if "file_path" in data and agent is not None:
            url = agent.FILE_URL.format(token=agent.token, file_path=data["file_path"])
        elif agent is not None:
            return agent.get_file(data["file_id"])
        else:
            url = None

        return cls(id=data["file_id"], url=url, size=data.get("file_size"))

    @classmethod
    async def a_parse(cls, data: dict, agent: Optional[TelegramAgent]=None):

        if "file_path" in data and agent is not None:
            url = agent.FILE_URL.format(token=agent.token, file_path=data["file_path"])
        elif agent is not None:
            return await agent.a_get_file(data["file_id"])
        else:
            url = None

        return cls(id=data["file_id"], url=url, size=data.get("file_size"))

    def render(self):

        if "id" in self.raw:
            return self.raw["id"]
        elif self.url is not None:
            return self.url
        elif self.filepath is not None:
            return open(self.filepath)

    async def a_render(self):

        if "id" in self.raw:
            return self.raw["id"]
        elif self.url is not None:
            return self.url
        elif self.filepath is not None:
            return open(self.filepath)

    @property
    def id(self):

        return self.raw["id"]

    @id.setter
    def id_setter(self, value: Optional[str]):

        if id is not None:
            self.raw["id"] = id
        else:
            del self.raw["id"]

    @property
    def size(self):

        return self.raw["size"]

    @size.setter
    def size_setter(self, value: Optional[int]):

        if value is not None:
            self.raw["size"] = value
        else:
            del self.raw["size"]


class TelegramLocation(Location):
    def __init__(self, latitude: float, longitude: float):

        super().__init__(latitude=latitude, longitude=longitude)

    @classmethod
    def parse(cls, data: dict):

        return cls(latitude=data["latitude"], longitude=data["longitude"])

    def render(self):

        return {"latitude": self.latitude, "longitude": self.longitude}


class TelegramContact:
    def __init__(self, phone: str, first_name: str, last_name: Optional[str]=None,
                 user_id: Optional[int]=None, vcard: Optional[str]=None):

        self.phone = phone
        self.first_name = first_name
        self.last_name = last_name
        self.user_id = user_id
        self.vcard = vcard
    
    @classmethod
    def parse(cls, data):

        return cls(
            phone=data["phone_number"],
            first_name=data["first_name"],
            last_name=data.get("last_name"),
            user_id=data.get("user_id"),
            vcard=data.get("vcard"),
        )

    def render(self):

        data = {"phone_number": self.phone, "first_name": self.first_name}
        if self.last_name is not None:
            data["last_name"] = self.last_name
        if self.user_id is not None:
            data["user_id"] = self.user_id
        if self.vcard is not None:
            data["vcard"] = self.vcard


# STOP HERE


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
    def __init__(self, text: str, url: Optional[str]=None, data: Optional[str]=None,
                 inline_query: Optional[str]=None, inline_chat: Optional[str]=None,
                 game: Optional[dict]=None):

        super().__init__(text=text, url=url, data=data, inline_query=inline_query,
                         inline_chat=inline_chat, game=game)

    def render(self):

        data = {"text": self.text}
        if "url" in self.raw:
            data["url"] = self.raw["url"]
        if "data" in self.raw:
            data["callback_data"] = self.raw["data"]
        if "inline_query" in self.raw:
            data["switch_inline_query"] = self.raw["inline_query"]
        if "inline_chat" in self.raw:
            data["switch_inline_query_current_chat"] = self.raw["inline_chat"]
        if "game" in self.raw:
            data["callback_game"] = self.raw["game"]
        return data
