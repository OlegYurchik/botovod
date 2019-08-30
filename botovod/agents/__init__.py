from __future__ import annotations
import asyncio
from datetime import datetime
import logging
from typing import Dict, Iterator, List, Tuple


class Agent:
    def __init__(self, message_storage: object=None,
                 logger: logging.Logger=logging.getLogger(__name__)):
        self.logger = logger
        self.botovod = None
        self.name = None
        self.running = False

        logger.info("Initialize agent %s", self)

    def __repr__(self) -> str:
        return self.__class__.__name__

    def listen(self, headers: Dict[str, str], body: str) -> Tuple[int, Dict[str, str], str]:
        from botovod.utils.exceptions import NotPassed

        self.logger.info("[%s:%s] Get updates.", self, self.name)

        messages = self.parser(headers, body)
        for chat, message in messages:
            for handler in self.botovod.handlers:
                try:
                    handler(self, chat, message)
                except NotPassed:
                    continue
                break
        return self.responser(headers, body)

    async def a_listen(self, headers: Dict[str, str], body: str) -> Tuple[int, Dict[str, str], str]:
        from botovod.utils.exceptions import NotPassed

        self.logger.info("[%s:%s] Get updates.", self, self.name)

        messages = await self.a_parser(headers, body)
        for chat, message in messages:
            for handler in self.botovod.handlers:
                try:
                    await handler(self, chat, message)
                except NotPassed:
                    continue
                break
        return await self.a_responser(headers, body)

    def start(self):
        raise NotImplementedError

    async def a_start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    async def a_stop(self):
        raise NotImplementedError

    def parser(self, headers: Dict[str, str], body: str) -> List[Tuple(Chat, Message)]:
        raise NotImplementedError

    async def a_parser(self, headers: Dict[str, str], body: str) -> List[Tuple(Chat, Message)]:
        raise NotImplementedError

    def responser(self, headers: Dict[str, str], body: str) -> Tuple[int, Dict[str, str], str]:
        raise NotImplementedError

    async def a_responser(self, headers: Dict[str, str],
                          body: str) -> Tuple[int, Dict[str, str], str]:
        raise NotImplementedError

    def send_message(self, chat: Chat, text: (str, None)=None, images: Iterator[Attachment]=[],
                     audios: Iterator[Attachment]=[], documents: Iterator[Attachment]=[],
                     videos: Iterator[Attachment]=[], locations: Iterator[Attachment]=[],
                     keyboard: (Keyboard, None)=None, **raw):
        raise NotImplementedError

    async def a_send_message(self, chat: Chat, text: (str, None)=None,
                             images: Iterator[Attachment]=[], audios: Iterator[Attachment]=[],
                             documents: Iterator[Attachment]=[], videos: Iterator[Attachment]=[],
                             locations: Iterator[Location]=[], keyboard: (Keyboard, None)=None,
                             **raw):
        raise NotImplementedError


class Chat:
    def __init__(self, agent: Agent, id: str, **raw):
        self.agent = agent
        self.id = id
        self.raw = dict(filter(lambda item: item[1] is not None, raw.items()))

class Message:
    def __init__(self, text: (str, None)=None, images: Iterator[Attachment]=[],
                 audios: Iterator[Attachment]=[], videos: Iterator[Attachment]=[],
                 documents: Iterator[Attachment]=[], locations: Iterator[Location]=[], **raw):
        self.text = text
        self.images = images
        self.audios = audios
        self.videos = videos
        self.documents = documents
        self.locations = locations
        self.raw = dict(filter(lambda item: item[1] is not None, raw.items()))


class Attachment:
    def __init__(self, url: (str, None)=None, filepath: (str, None)=None, **raw):
        self.url = url
        self.filepath = filepath
        self.raw = dict(filter(lambda item: item[1] is not None, raw.items()))


class Location:
    def __init__(self, latitude: float, longitude: float, **raw):
        self.latitude = latitude
        self.longitude = longitude
        self.raw = dict(filter(lambda item: item[1] is not None, raw.items()))


class Keyboard:
    def __init__(self, buttons: Iterator[Iterator[KeyboardButton]], **raw):
        self.buttons = buttons
        self.raw = dict(filter(lambda item: item[1] is not None, raw.items()))


class KeyboardButton:
    def __init__(self, text: str, **raw):
        self.text = text
        self.raw = dict(filter(lambda item: item[1] is not None, raw.items()))
