from __future__ import annotations
import asyncio
import logging
from typing import Dict, Iterator, List, Tuple


class Agent:
    def __init__(self, logger: logging.Logger=logging.getLogger(__name__)):
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

    def send_message(self, chat: Chat, text: (str, None)=None, images: Iterator[Image]=[],
                     audios: Iterator[Audio]=[], documents: Iterator[Document]=[],
                     videos: Iterator[Video]=[], locations: Iterator[Location]=[],
                     keyboard: (Keyboard, None)=None, raw: (dict, None)=None):
        raise NotImplementedError

    async def a_send_message(self, chat: Chat, text: (str, None)=None, images: Iterator[Image]=[],
                             audios: Iterator[Audio]=[], documents: Iterator[Document]=[],
                             videos: Iterator[Video]=[], locations: Iterator[Location]=[],
                             keyboard: (Keyboard, None)=None, raw: (dict, None)=None):
        raise NotImplementedError


class Entity:
    def __init__(self):
        self.raw = {}


class Chat(Entity):
    def __init__(self, agent: Agent, id: str):
        self.agent = agent
        self.id = id


class Message(Entity):
    def __init__(self):
        super().__init__()
        self.text = None
        self.images = []
        self.audios = []
        self.videos = []
        self.documents = []
        self.locations = []
        self.date = None


class Attachment(Entity):
    url = None
    file = None


class Image(Attachment):
    pass


class Audio(Attachment):
    pass


class Video(Attachment):
    pass


class Document(Attachment):
    pass


class Location(Entity):
    def __init__(self, latitude: float, longitude: float):
        super().__init__()
        self.latitude = latitude
        self.longitude = longitude


class Keyboard(Entity):
    def __init__(self, *buttons: Iterator[KeyboardButton]):
        super().__init__()
        self.buttons = buttons


class KeyboardButton(Entity):
    def __init__(self, text: str):
        super().__init__()
        self.text = text
