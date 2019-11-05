from __future__ import annotations
from ..exceptions import HandlerNotPassed
import asyncio
from datetime import datetime
import logging
from typing import Dict, Iterator, List, Optional, Tuple


class Agent:
    def __init__(self, logger: Optional[logging.Logger]=None):

        self.logger = logger
        self.botovod = None
        self.name = None
        self.running = False

        if logger:
            logger.info("Initialize agent %s", self)

    def __repr__(self) -> str:

        return self.__class__.__name__

    def listen(self, headers: Dict[str, str], body: str) -> Tuple[int, Dict[str, str], str]:

        if self.logger:
            self.logger.debug("[%s:%s] Get request.", self, self.name)

        messages = self.parser(headers, body)
        for chat, message in messages:
            if self.botovod.dbdriver:
                follower = self.botovod.dbdriver.get_follower(self, chat)
                if not follower:
                    follower = self.botovod.dbdriver.add_follower(self, chat)
            else:
                follower = None
            for handler in self.botovod._handlers.values():
                try:
                    handler(self, chat, message, follower)
                except HandlerNotPassed:
                    continue
                break

        return self.responser(headers, body)

    async def a_listen(self, headers: Dict[str, str], body: str) -> Tuple[int, Dict[str, str], str]:

        if self.logger:
            self.logger.debug("[%s:%s] Get updates.", self, self.name)

        messages = await self.a_parser(headers, body)
        for chat, message in messages:
            if self.botovod.dbdriver is not None:
                follower = await self.botovod.dbdriver.a_get_follower(self, chat)
                if follower is None:
                    follower = await self.botovod.dbdriver.a_add_follower(self, chat)
            else:
                follower = None
            for handler in self.botovod._handlers.values():
                try:
                    await handler(self, chat, message, follower)
                except HandlerNotPassed:
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

    def send_message(self, chat: Chat, text: Optional[str]=None, images: Iterator[Attachment]=(),
                     audios: Iterator[Attachment]=(), documents: Iterator[Attachment]=(),
                     videos: Iterator[Attachment]=(), locations: Iterator[Attachment]=(),
                     keyboard: Optional[Keyboard]=None, **raw):

        raise NotImplementedError

    async def a_send_message(self, chat: Chat, text: Optional[str]=None,
                             images: Iterator[Attachment]=(), audios: Iterator[Attachment]=(),
                             documents: Iterator[Attachment]=(), videos: Iterator[Attachment]=(),
                             locations: Iterator[Location]=(), keyboard: Optional[Keyboard]=None,
                             **raw):

        raise NotImplementedError


class Chat:
    def __init__(self, agent: Agent, id: str, **raw):
        
        self.agent = agent
        self.id = id
        self.raw = dict(filter(lambda item: item[1] is not None, raw.items()))


class Message:
    def __init__(self, text: Optional[str]=None, images: Iterator[Attachment]=(),
                 audios: Iterator[Attachment]=(), videos: Iterator[Attachment]=(),
                 documents: Iterator[Attachment]=(), locations: Iterator[Location]=(), **raw):

        self.text = text
        self.images = images
        self.audios = audios
        self.videos = videos
        self.documents = documents
        self.locations = locations
        self.raw = dict(filter(lambda item: item[1] is not None, raw.items()))


class Attachment:
    def __init__(self, url: Optional[str]=None, filepath: Optional[str]=None, **raw):

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
