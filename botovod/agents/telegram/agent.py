from __future__ import annotations
import asyncio
import io
import json
import time
from threading import Thread
from typing import Dict, IO, Iterator, List, Optional, Tuple

import aiohttp
import requests

from botovod.agents import Agent, Attachment, Chat, Keyboard, Location, Message
from .types import (TelegramAttachment, TelegramCallback, TelegramChat, TelegramInlineKeyboard,
                    TelegramKeyboard, TelegramMessage, TelegramUser)


class Requester:
    BASE_URL = "https://api.telegram.org/bot{token}/{method}"
    FILE_URL = "https://api.telegram.org/file/bot{token}/{path}"

    def __init__(self, logger):
        self.logger = logger

    def do_method(self, token: str, method: str, payload: Optional[dict] = None,
                  files: Optional[Dict[str, IO]] = None):
        url = self.BASE_URL.format(token=token, method=method)

        response = requests.post(url, data=payload, files=files)
        data = response.json()
        if data["ok"]:
            return data["result"]

    async def a_do_method(self, token: str, method: str, payload: Optional[dict] = None,
                          files: Optional[Dict[str, IO]] = None):
        url = self.BASE_URL.format(token=token, method=method)

        if payload is not None and files is not None:
            payload.update(files)
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=payload) as response:
                data = await response.json()
        if data["ok"]:
            return data["result"]

    def get_file(self, token: str, path: str):
        url = self.FILE_URL.format(token=token, path=path)

        response = requests.get(url)
        response.raise_for_status()
        return response.content

    async def a_get_file(self, token: str, path: str):
        url = self.FILE_URL.format(token=token, path=path)

        async with aiohttp.ClientSession(raist_for_status=True) as session:
            async with session.get(url) as response:
                return await response.read()


class TelegramAgent(Agent):
    WEBHOOK = "webhook"
    POLLING = "polling"

    def __init__(self, token: str, method: str = POLLING, delay: int = 5,
                 webhook_url: Optional[str] = None, certificate_path: Optional[str] = None):
        super().__init__()
        self.requester = Requester(logger=self.logger)
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
        self.set_webhook()
        self.running = True
        if self.method == self.POLLING:
            self.thread = Thread(target=self.polling)
            self.thread.start()

        self.logger.info("Started %s by %s.", self.name, self.method)
        self.thread.join()

    async def a_start(self):
        await self.a_set_webhook()
        self.running = True
        if self.method == self.POLLING:
            asyncio.get_running_loop().create_task(self.a_polling())

        self.logger.info("Started %s by %s.", self.name, self.method)

    def stop(self):
        if self.method == self.POLLING:
            self.thread.join()
            self.thread = None
        self.running = False

        self.logger.info("Agent %s stopped.", self.name)

    async def a_stop(self):
        self.running = False

        self.logger.info("Agent %s stopped.", self.name)

    def parser(self, headers: Dict[str, str],
               body: str) -> List[Tuple[Chat, Message]]:
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
                       body: str) -> List[Tuple[Chat, Agent]]:
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
        while self.running:
            try:
                payload = {"offset": self.last_update + 1} if self.last_update > 0 else {}
                updates = self.requester.do_method(token=self.token, method="getUpdates",
                                                   payload=payload)
                for update in updates:
                    self.listen(headers={}, body=json.dumps(update), **self.botovod._items)
            except Exception:
                self.logger.exception("Got exception")
            finally:
                time.sleep(self.delay)

    async def a_polling(self):
        while self.running:
            try:
                payload = {"offset": self.last_update + 1} if self.last_update > 0 else {}
                updates = await self.requester.a_do_method(token=self.token, method="getUpdates",
                                                           payload=payload)
                for update in updates:
                    await self.a_listen(headers={}, body=json.dumps(update), **self.botovod._items)
            except Exception:
                self.logger.exception("Got exception")
            finally:
                await asyncio.sleep(self.delay)

    def set_webhook(self):
        payload = {}
        files = {}
        if self.method == self.WEBHOOK:
            payload["url"] = self.webhook_url
            if self.certificate_path is not None:
                files["certificate"] = open(self.certificate_path)
        try:
            self.requester.do_method(token=self.token, method="setWebhook", payload=payload,
                                     files=files)
        finally:
            if files:
                files["certificate"].close()

        self.logger.info("Set %s webhook.", self.name)

    async def a_set_webhook(self):
        payload = {}
        files = {}
        if self.method == self.WEBHOOK:
            payload["url"] = self.webhook_url
            if self.certificate_path is not None:
                files["certificate"] = open(self.certificate_path)
        try:
            await self.requester.a_do_method(token=self.token, method="setWebhook",
                                             payload=payload, files=files)
        finally:
            if files:
                files["certificate"].close()

        self.logger.info("Set %s webhook.", self.name)

    def get_webhook_info(self):
        return self.requester.do_method(token=self.token, method="getWebhookInfo")

    async def a_get_webhook_info(self):
        return await self.requester.a_do_method(token=self.token, method="getWebhookInfo")

    def get_me(self):
        data = self.requester.do_method(token=self.token, method="getMe")
        if data is not None:
            return TelegramUser.parse(agent=self, data=data)

    async def a_get_me(self):
        data = await self.requester.a_do_method(token=self.token, method="getMe")
        if data is not None:
            return TelegramUser.parse(agent=self, data=data)

    def send_message(self, chat: Chat, text: Optional[str] = None,
                     images: Iterator[Attachment] = (), audios: Iterator[Attachment] = (),
                     documents: Iterator[Attachment] = (), videos: Iterator[Attachment] = (),
                     locations: Iterator[Location] = (), keyboard: Optional[Keyboard] = None,
                     html: bool = False, markdown: bool = False, web_preview: bool = True,
                     notification: bool = True, reply: Optional[Message] = None,
                     remove_keyboard: bool = False):
        messages = []
        if text is not None:
            payload = {
                "chat_id": chat.id,
                "text": text,
                "disable_web_page_preview": not web_preview,
                "disable_notification": not notification, 
            }
            if keyboard is not None:
                if hasattr(keyboard, "render"):
                    payload["reply_markup"] = keyboard.render()
                else:
                    payload["reply_markup"] = TelegramKeyboard.default_render(keyboard)
            elif remove_keyboard:
                payload["reply_markup"] = '{"remove_keyboard": true}'
            if html:
                payload["parse_mode"] = "HTML"
            elif markdown:
                payload["parse_mode"] = "Markdown"
            if reply is not None:
                payload["reply_to_message_id"] = reply.raw["id"]
            data = self.requester.do_method(token=self.token, method="sendMessage", payload=payload)
            if data is not None:
                messages.append(TelegramMessage.parse(data))
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

    async def a_send_message(self, chat: Chat, text: Optional[str] = None,
                             images: Iterator[Attachment] = (), audios: Iterator[Attachment] = (),
                             documents: Iterator[Attachment] = (),
                             videos: Iterator[Attachment] = (), locations: Iterator[Location] = (),
                             keyboard: Optional[Keyboard] = None, html: bool = False,
                             markdown: bool = False, web_preview: bool = True,
                             notification: bool = True, reply: Optional[Message] = None,
                             remove_keyboard: bool = False):
        messages = []
        if text is not None:
            payload = {
                "chat_id": chat.id,
                "text": text,
                "disable_web_page_preview": not web_preview,
                "disable_notification": not notification, 
            }
            if keyboard is not None:
                if hasattr(keyboard, "render"):
                    payload["reply_markup"] = keyboard.render()
                else:
                    payload["reply_markup"] = TelegramKeyboard.default_render(keyboard)
            elif remove_keyboard:
                payload["reply_markup"] = '{"remove_keyboard": true}'
            if html:
                payload["parse_mode"] = "HTML"
            elif markdown:
                payload["parse_mode"] = "Markdown"
            if reply is not None:
                payload["reply_to_message_id"] = reply.raw["id"]
            data = await self.requester.a_do_method(token=self.token, method="sendMessage",
                                                    payload=payload)
            if data is not None:
                messages.append(TelegramMessage.parse(data))
        for image in images:
            message = await self.a_send_photo(chat, image, keyboard=keyboard,
                                              remove_keyboard=remove_keyboard)
            if message is not None:
                messages.append(message)
        for audio in audios:
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
                        keyboard: Optional[Keyboard] = None, remove_keyboard: bool = False):

        attachment_data = TelegramAttachment.render(attachment)

        payload = {"chat_id": chat.id}
        files = {}
        if isinstance(attachment_data, io.IOBase):
            files = {type: attachment_data}
        else:
            payload[type] = attachment_data

        if keyboard is not None:
            if hasattr(keyboard, "render"):
                payload["reply_markup"] = keyboard.render()
            else:
                payload["reply_markup"] = TelegramKeyboard.default_render(keyboard)
        elif remove_keyboard:
            payload["reply_markup"] = '{"remove_keyboard": true}'

        data = self.requester.do_method(token=self.token, method="send"+type.capitalize(),
                                        payload=payload, files=files)
        if data is not None:
            return TelegramMessage.parse(data)

    async def a_send_attachment(self, type: str, chat: Chat, attachment: Attachment,
                                keyboard: Optional[Keyboard] = None, remove_keyboard: bool = False):
        attachment_data = await TelegramAttachment.a_render(attachment)

        payload = {"chat_id": chat.id}
        files = {}
        if isinstance(attachment_data, io.IOBase):
            files = {type: attachment_data}
        else:
            payload[type] = attachment_data

        if keyboard is not None:
            if hasattr(keyboard, "render"):
                payload["reply_markup"] = keyboard.render()
            else:
                payload["reply_markup"] = TelegramKeyboard.default_render(keyboard)
        elif remove_keyboard:
            payload["reply_markup"] = '{"remove_keyboard": true}'

        data = await self.requester.a_do_method(token=self.token, method="send"+type.capitalize(),
                                                payload=payload, files=files)
        if data is not None:
            return await TelegramMessage.a_parse(data)

    def send_photo(self, chat: Chat, image: Attachment, keyboard: Optional[Keyboard] = None,
                   remove_keyboard: bool = False):
        return self.send_attachment(
            type="photo",
            chat=chat,
            attachment=image,
            keyboard=keyboard,
            remove_keyboard=remove_keyboard,
        )

    async def a_send_photo(self, chat: Chat, image: Attachment, keyboard: Optional[Keyboard] = None,
                           remove_keyboard: bool = False):
        return await self.a_send_attachment(
            type="photo",
            chat=chat,
            attachment=image,
            keyboard=keyboard,
            remove_keyboard=remove_keyboard,
        )

    def send_audio(self, chat: Chat, audio: Attachment, keyboard: Optional[Keyboard] = None,
                   remove_keyboard: bool = False):
        return self.send_attachment(
            type="audio",
            chat=chat,
            attachment=audio,
            keyboard=keyboard,
            remove_keyboard=remove_keyboard,
        )

    async def a_send_audio(self, chat: Chat, audio: Attachment, keyboard: Optional[Keyboard] = None,
                           remove_keyboard: bool = False):
        return await self.a_send_attachment(
            type="audio",
            chat=chat,
            attachment=audio,
            keyboard=keyboard,
            remove_keyboard=remove_keyboard,
        )

    def send_document(self, chat: Chat, document: Attachment, keyboard: Optional[Keyboard] = None,
                      remove_keyboard: bool = False):
        return self.send_attachment(
            type="document",
            chat=chat,
            attachment=document,
            keyboard=keyboard,
            remove_keyboard=remove_keyboard,
        )

    async def a_send_document(self, chat: Chat, document: Attachment,
                              keyboard: Optional[Keyboard] = None, remove_keyboard: bool = False):
        return await self.a_send_attachment(
            type="document",
            chat=chat,
            attachment=document,
            keyboard=keyboard,
            remove_keyboard=remove_keyboard,
        )

    def send_video(self, chat: Chat, video: Attachment, keyboard: Optional[Keyboard] = None,
                   remove_keyboard: bool = False):
        return self.send_attachment(
            type="video",
            chat=chat,
            attachment=video,
            keyboard=keyboard,
            remove_keyboard=remove_keyboard,
        )

    async def a_send_video(self, chat: Chat, video: Attachment, keyboard: Optional[Keyboard] = None,
                           remove_keyboard: bool = False):
        return await self.a_send_attachment(
            type="video",
            chat=chat,
            attachment=video,
            keyboard=keyboard,
            remove_keyboard=remove_keyboard,
        )

    def send_location(self, chat: Chat, location: Location, keyboard: Optional[Keyboard] = None,
                      remove_keyboard: bool = True):
        payload = {
            "chat_id": chat.id,
            "longitude": location.longitude,
            "latitude": location.latitude,
        }
        if keyboard is not None:
            if hasattr(keyboard, "render"):
                payload["reply_markup"] = keyboard.render()
            else:
                payload["reply_markup"] = TelegramKeyboard.default_render(keyboard)
        elif remove_keyboard:
            payload["reply_markup"] = '{"remove_keyboard": true}'
        data = self.requester.do_method(token=self.token, method="sendLocation", payload=payload)
        if data is not None:
            return TelegramMessage.parse(data)

    async def a_send_location(self, chat: Chat, location: Location,
                              keyboard: Optional[Keyboard] = None, remove_keyboard: bool = False):
        payload = {
            "chat_id": chat.id,
            "longitude": location.longitude,
            "latitude": location.latitude,
        }
        if keyboard is not None:
            if hasattr(keyboard, "render"):
                payload["reply_markup"] = keyboard.render()
            else:
                payload["reply_markup"] = TelegramKeyboard.default_render(keyboard)
        elif remove_keyboard:
            payload["reply_markup"] = '{"remove_keyboard": true}'
        data = await self.requester.a_do_method(token=self.token, method="sendLocation",
                                                payload=payload)
        if data is not None:
            return await TelegramMessage.a_parse(data)

    def get_file(self, file_id: int):
        data = self.requester.do_method(
            token=self.token,
            method="getFile",
            payload={"file_id": file_id},
        )
        return TelegramAttachment.parse(data, agent=self)

    async def a_get_file(self, file_id: int):
        data = await self.requester.a_do_method(
            token=self.token,
            method="getFile",
            payload={"file_id": file_id},
        )
        return await TelegramAttachment.a_parse(data, agent=self)

    def edit_message_text(self, chat: Chat, message: TelegramMessage, text: str,
                          keyboard: Optional[TelegramInlineKeyboard] = None, html: bool = False,
                          markdown: bool = False, web_preview: bool = True):
        payload = {
            "chat_id": chat.id,
            "message_id": message.raw["id"],
            "text": text,
            "disable_web_page_preview": not web_preview,
        }
        if keyboard is not None:
            payload["reply_markup"] = keyboard.render()
        if html:
            payload["parse_mode"] = "HTML"
        elif markdown:
            payload["parse_mode"] = "Markdown"
        self.requester.do_method(token=self.token, method="editMessageText", payload=payload)

    async def a_edit_message_text(self, chat: Chat, message: TelegramMessage, text: str,
                                  keyboard: Optional[TelegramInlineKeyboard] = None,
                                  html: bool = False, markdown: bool = False,
                                  web_preview: bool = True):
        payload = {
            "chat_id": chat.id,
            "message_id": message.raw["id"],
            "text": text,
            "disable_web_page_preview": not web_preview,
        }
        if keyboard is not None:
            payload["reply_markup"] = keyboard.render()
        if html:
            payload["parse_mode"] = "HTML"
        elif markdown:
            payload["parse_mode"] = "Markdown"
        await self.requester.a_do_method(
            token=self.token,
            method="editMessageText",
            payload=payload,
        )

    def edit_message_caption(self, chat: Chat, message: TelegramMessage, caption: str,
                             keyboard: Optional[TelegramInlineKeyboard] = None, html: bool = False,
                             markdown: bool = False):
        payload = {"chat_id": chat.id, "message_id": message.raw["id"], "caption": caption}
        if keyboard is not None:
            payload["reply_markup"] = keyboard.render()
        if html:
            payload["parse_mode"] = "HTML"
        elif markdown:
            payload["parse_mode"] = "Markdown"
        self.requester.do_method(token=self.token, method="editMessageCaption", payload=payload)

    async def a_edit_message_caption(self, chat: Chat, message: TelegramMessage, caption: str,
                                     keyboard: Optional[TelegramInlineKeyboard] = None,
                                     html: bool = False, markdown: bool = False):
        payload = {"chat_id": chat.id, "message_id": message.raw["id"], "caption": caption}
        if keyboard is not None:
            payload["reply_markup"] = keyboard.render()
        if html:
            payload["parse_mode"] = "HTML"
        elif markdown:
            payload["parse_mode"] = "Markdown"
        await self.requester.a_do_method(token=self.token, method="editMessageCaption",
                                         payload=payload)

    def edit_message_media(self, chat: Chat, message: TelegramMessage, media: Attachment, type: str,
                           thumb: Optional[Attachment] = None, caption: Optional[str] = None,
                           markdown: bool = False, html: bool = False,
                           keyboard: Optional[TelegramInlineKeyboard] = None, **raw):
        attachment_data = TelegramAttachment.render(media)
        thumb_data = TelegramAttachment(thumb) if thumb else None

        payload = {"chat_id": chat.id, "message_id": message.id}
        media_payload = {"type": type}
        files = {}
        if isinstance(attachment_data, io.IOBase):
            files["media"] = attachment_data
        else:
            media_payload["media"] = attachment_data
        if isinstance(thumb_data, io.IOBase):
            files["thumb"] = thumb_data
        else:
            media_payload["thumb"] = thumb_data

        if caption is not None:
            media_payload["caption"] = caption
        if markdown:
            media_payload["parse_mode"] = "Markdown"
        elif html:
            media_payload["parse_mode"] = "HTML"
        media_payload.update(raw)
        if keyboard is not None:
            payload["reply_markup"] = keyboard.render()
        payload["media"] = json.dumps(media_payload)

        self.requester.do_method(token=self.token, method="editMessageMedia", payload=payload,
                                 files=files)

    async def a_edit_message_media(self, chat: Chat, message: TelegramMessage, media: Attachment,
                                   type: str, thumb: Optional[Attachment] = None,
                                   caption: Optional[str] = None, markdown: bool = False,
                                   html: bool = False,
                                   keyboard: Optional[TelegramInlineKeyboard] = None, **raw):
        attachment_data = await TelegramAttachment.a_render(media)
        thumb_data = await TelegramAttachment.a_render(thumb) if thumb else None

        payload = {"chat_id": chat.id, "message_id": message.id}
        media_payload = {"type": type, "media": attachment_data}
        files = {}
        if isinstance(attachment_data, io.IOBase):
            files["media"] = attachment_data
        else:
            media_payload["media"] = attachment_data
        if isinstance(thumb_data, io.IOBase):
            files["thumb"] = thumb_data
        elif thumb_data:
            media_payload["thumb"] = thumb_data
        if caption:
            media_payload["caption"] = caption
        if markdown:
            media_payload["parse_mode"] = "Markdown"
        elif html:
            media_payload["parse_mode"] = "HTML"
        media_payload.update(raw)
        if keyboard:
            payload["reply_markup"] = keyboard.render()
        payload["media"] = json.dumps(media_payload)
        await self.requester.a_do_method(token=self.token, method="edtMessageMedia",
                                         payload=payload, files=files)

    def edit_message_image(self, chat: Chat, message: TelegramMessage, image: Attachment,
                           caption: Optional[str] = None, markdown: bool = False,
                           html: bool = False, keyboard: Optional[TelegramInlineKeyboard] = None):
        return self.edit_message_media(chat=chat, message=message, media=image, type="photo",
                                       caption=caption, markdown=markdown, html=html,
                                       keyboard=keyboard)

    async def a_edit_message_image(self, chat: Chat, message: TelegramMessage, image: Attachment,
                                   caption: Optional[str] = None, markdown: bool = False,
                                   html: bool = False,
                                   keyboard: Optional[TelegramInlineKeyboard] = None):
        return await self.a_edit_message_media(chat=chat, message=message, media=image,
                                               type="photo", caption=caption, markdown=markdown,
                                               html=html, keyboard=keyboard)

    def edit_message_video(self, chat: Chat, message: TelegramMessage, video: Attachment,
                           thumb: Optional[Attachment] = None, caption: Optional[str] = None,
                           markdown: bool = False, html: bool = False, width: Optional[int] = None,
                           height: Optional[int] = None, duration: Optional[int] = None,
                           supports_streaming: Optional[bool] = None,
                           keyboard: Optional[TelegramInlineKeyboard] = None):
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
                                   thumb: Optional[Attachment] = None,
                                   caption: Optional[str] = None, markdown: bool = False,
                                   html: bool = False, width: Optional[int] = None,
                                   height: Optional[int] = None, duration: Optional[int] = None,
                                   supports_streaming: Optional[bool] = None,
                                   keyboard: Optional[TelegramInlineKeyboard] = None):
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
                               thumb: Optional[Attachment] = None, caption: Optional[str] = None,
                               markdown: bool = False, html: bool = False,
                               width: Optional[int] = None, height: Optional[int] = None,
                               duration: Optional[int] = None,
                               keyboard: Optional[TelegramInlineKeyboard] = None):
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
                                       animation: Attachment, thumb: Optional[Attachment] = None,
                                       caption: Optional[str] = None, markdown: bool = False,
                                       html: bool = False, width: Optional[int] = None,
                                       height: Optional[int] = None, duration: Optional[int] = None,
                                       keyboard: Optional[TelegramInlineKeyboard] = None):
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
                           thumb: Optional[Attachment] = None, caption: Optional[str] = None,
                           markdown: bool = False, html: bool = False,
                           duration: Optional[int] = None, performer: Optional[str] = None,
                           title: Optional[str] = None,
                           keyboard: Optional[TelegramInlineKeyboard] = None):
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
                                   audio: Attachment, thumb: Optional[Attachment] = None,
                                   caption: Optional[str] = None, markdown: bool = False,
                                   html: bool = False, duration: Optional[int] = None,
                                   performer: Optional[str] = None, title: Optional[str] = None,
                                   keyboard: Optional[TelegramInlineKeyboard] = None):
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
                              thumb: Optional[Attachment] = None, caption: Optional[str] = None,
                              markdown: bool = False, html: bool = False,
                              keyboard: Optional[TelegramInlineKeyboard] = None):
        return self.edit_message_media(chat=chat, message=message, media=document, type="document",
                                       thumb=thumb, caption=caption, markdown=markdown, html=html,
                                       keyboard=keyboard)

    async def a_edit_message_document(self, chat: Chat, message: TelegramMessage,
                                      document: Attachment, thumb: Optional[Attachment] = None,
                                      caption: Optional[str] = None, markdown: bool = False,
                                      html: bool = False,
                                      keyboard: Optional[TelegramInlineKeyboard] = None):
        return await self.a_edit_message_media(chat=chat, message=message, media=document,
                                               type="document", thumb=thumb, caption=caption,
                                               markdown=markdown, html=html, keyboard=keyboard)

    def edit_message_keyboard(self, chat: Chat, message: TelegramMessage,
                              keyboard: TelegramInlineKeyboard):
        payload = {
            "chat_id": chat.id,
            "message_id": message.raw["id"],
            "reply_markup": keyboard.render(),
        }
        self.requester.do_method(token=self.token, method="editMessageReplyMarkup", payload=payload)

    async def a_edit_message_keyboard(self, chat: Chat, message: TelegramMessage,
                                      keyboard: TelegramInlineKeyboard):
        payload = {
            "chat_id": chat.id,
            "message_id": message.raw["id"],
            "reply_markup": keyboard.render(),
        }
        await self.requester.a_do_method(token=self.token, method="editMessageReplyMarkup",
                                         payload=payload)

    def delete_message(self, chat: Chat, message: TelegramMessage):
        payload = {"chat_id": chat.id, "message_id": message.raw["id"]}
        self.requester.do_method(token=self.token, method="deleteMessage", payload=payload)

    async def a_delete_message(self, chat: Chat, message: TelegramMessage):
        payload = {"chat_id": chat.id, "message_id": message.raw["id"]}
        await self.requester.a_do_method(token=self.token, method="deleteMessage", payload=payload)

    def send_chat_action(self, chat: Chat, action: str):
        payload = {"chat_id": chat.id, "action": action}
        self.requester.do_method(token=self.token, method="sendChatAction", payload=payload)

    async def a_send_chat_action(self, chat: Chat, action: str):
        payload = {"chat_id": chat.id, "action": action}
        await self.requester.a_do_method(token=self.token, method="sendChatAction", payload=payload)

    def send_sticker(self, chat: Chat, sticker: Attachment, keyboard: Optional[Keyboard] = None,
                     remove_keyboard: bool = False):
        return self.send_attachment(
            type="sticker",
            chat=chat,
            attachment=sticker,
            keyboard=keyboard,
            remove_keyboard=remove_keyboard,
        )

    async def a_send_sticker(self, chat: Chat, sticker: Attachment,
                             keyboard: Optional[Keyboard] = None, remove_keyboard: bool = False):
        return await self.a_send_attachment(
            type="sticker",
            chat=chat,
            attachment=sticker,
            keyboard=keyboard,
            remove_keyboard=remove_keyboard,
        )

    """
    def get_me(self):
        pass

    def forward_message(self, to_chat, from_chat, message):
        pass
    
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
