from __future__ import annotations
import logging
from typing import Dict, Iterator, List, Optional, Tuple

from botovod.exceptions import HandlerNotPassed
from .types import Attachment, Chat, Keyboard, Location, Message


class Agent:
    def __init__(self):
        self.botovod = None
        self.running = False
        self.name = None

        self.logger = logging.getLogger(__name__)

    def __repr__(self) -> str:
        return self.__class__.__name__

    def listen(self, headers: Dict[str, str], body: str, **scope) -> Tuple[int, Dict[str, str], str]:
        self.logger.debug("Get request")

        messages = self.parser(headers, body)
        for chat, message in messages:
            follower = None
            if self.botovod.dbdriver:
                follower = self.botovod.dbdriver.get_follower(self, chat)
                if not follower:
                    follower = self.botovod.dbdriver.add_follower(self, chat)
            for handler in self.botovod.handlers:
                try:
                    handler(self, chat, message, follower, **scope)
                except HandlerNotPassed:
                    continue
                break

        return self.responser(headers, body)

    async def a_listen(self, headers: Dict[str, str], body: str, **scope) -> Tuple[int, Dict[str, str], str]:
        self.logger.debug("Get updates")

        messages = await self.a_parser(headers, body)
        for chat, message in messages:
            if self.botovod.dbdriver is not None:
                follower = await self.botovod.dbdriver.a_get_follower(self, chat)
                if follower is None:
                    follower = await self.botovod.dbdriver.a_add_follower(self, chat)
            else:
                follower = None
            for handler in self.botovod.handlers:
                try:
                    await handler(self, chat, message, follower, **scope)
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

    def parser(self, headers: Dict[str, str], body: str) -> List[Tuple[Chat, Message]]:
        raise NotImplementedError

    async def a_parser(self, headers: Dict[str, str], body: str) -> List[Tuple[Chat, Message]]:
        raise NotImplementedError

    def responser(self, headers: Dict[str, str], body: str) -> Tuple[int, Dict[str, str], str]:
        raise NotImplementedError

    async def a_responser(self, headers: Dict[str, str],
                          body: str) -> Tuple[int, Dict[str, str], str]:
        raise NotImplementedError

    def send_message(self, chat: Chat, text: Optional[str] = None,
                     images: Iterator[Attachment] = (),
                     audios: Iterator[Attachment] = (), documents: Iterator[Attachment] = (),
                     videos: Iterator[Attachment] = (), locations: Iterator[Location] = (),
                     keyboard: Optional[Keyboard] = None, **raw):
        raise NotImplementedError

    async def a_send_message(self, chat: Chat, text: Optional[str] = None,
                             images: Iterator[Attachment] = (), audios: Iterator[Attachment] = (),
                             documents: Iterator[Attachment] = (),
                             videos: Iterator[Attachment] = (),
                             locations: Iterator[Location] = (),
                             keyboard: Optional[Keyboard] = None,
                             **raw):
        raise NotImplementedError
