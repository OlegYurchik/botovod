from __future__ import annotations
from botovod.agents import Agent, Attachment, Chat, Location
from datetime import datetime
from typing import Any, Dict, Iterable, Optional


class Follower:
    def get_chat(self) -> Chat:

        raise NotImplementedError

    async def a_get_chat(self) -> Chat:

        raise NotImplementedError

    def get_dialog(self) -> Optional[str]:

        raise NotImplementedError

    async def a_get_dialog(self) -> Optional[str]:

        raise NotImplementedError

    def set_dialog(self, name: Optional[str]=None):

        raise NotImplementedError

    async def a_set_dialog(self, name: Optional[str]=None):

        raise NotImplementedError

    def get_next_step(self) -> Optional[str]:

        raise NotImplementedError

    async def a_get_next_step(self) -> Optional[str]:

        raise NotImplementedError

    def set_next_step(self, next_step: Optional[str]=None):

        raise NotImplementedError

    async def a_set_next_step(self, next_step: Optional[str]=None):

        raise NotImplementedError

    def get_history(self, after: Optional[datetime]=None, before: Optional[datetime]=None,
                    input: Optional[bool]=None, text: Optional[str]=None):

        raise NotImplementedError

    async def a_get_history(self, after: Optional[datetime]=None, before: Optional[datetime]=None,
                            input: Optional[bool]=None, text: Optional[str]=None):

        raise NotImplementedError

    def add_history(self, datetime: datetime, text: Optional[str]=None,
                    images: Iterable[Attachment]=(), audios: Iterable[Attachment]=(),
                    videos: Iterable[Attachment]=(), documents: Iterable[Attachment]=(),
                    locations: Iterable[Location]=(), input: bool=True, **raw):

        raise NotImplementedError

    async def a_add_history(self, datetime: datetime, text: Optional[str]=None,
                            images: Iterable[Attachment]=(), audios: Iterable[Attachment]=(),
                            videos: Iterable[Attachment]=(), documents: Iterable[Attachment]=(),
                            locations: Iterable[Location]=(), input: bool=True, **raw):

        raise NotImplementedError

    def clear_history(self, after: Optional[datetime]=None, before: Optional[datetime]=None,
                      input: Optional[bool]=None, text: Optional[str]=None):

        raise NotImplementedError

    async def a_clear_history(self, after: Optional[datetime]=None, before: Optional[datetime]=None,
                              input: Optional[bool]=None, text: Optional[str]=None):

        raise NotImplementedError

    def get_values(self) -> Dict[str, str]:

        raise NotImplementedError

    async def a_get_values(self) -> Dict[str, str]:

        raise NotImplementedError

    def get_value(self, name: str) -> str:

        raise NotImplementedError

    async def a_get_value(self, name: str) -> str:

        raise NotImplementedError

    def set_value(self, name: str, value: str):

        raise NotImplementedError

    async def a_set_value(self, name: str, value: str):

        raise NotImplementedError

    def delete_value(self, name: str):

        raise NotImplementedError

    async def a_delete_value(self, name: str):

        raise NotImplementedError

    def clear_values(self):

        raise NotImplementedError

    async def a_clear_values(self):

        raise NotImplementedError


class DBDriver:
    @classmethod
    def connect(cls, **settings) -> DBDriver:

        raise NotImplementedError

    @classmethod
    async def a_connect(cls, **settings) -> DBDriver:

        raise NotImplementedError

    @classmethod
    def get_follower(cls, agent: Agent, chat: Chat) -> Follower:

        raise NotImplementedError

    @classmethod
    async def a_get_follower(cls, agent: Agent, chat: Chat) -> Follower:

        raise NotImplementedError

    @classmethod
    def add_follower(cls, agent: Agent, chat: Chat) -> Follower:

        raise NotImplementedError

    @classmethod
    async def a_add_follower(cls, agent: Agent, chat: Chat) -> Follower:

        raise NotImplementedError

    @classmethod
    def delete_follower(cls, agent: Agent, chat: Chat):

        raise NotImplementedError

    @classmethod
    async def a_delete_follower(cls, agent: Agent, chat: Chat):

        raise NotImplementedError
