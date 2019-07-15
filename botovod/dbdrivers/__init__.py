from botovod.agents import Agent, Audio, Chat, Document, Image, Location, Video
from datetime import datetime
from typing import Any, Dict, Iterable


class Follower:
    def get_chat(self) -> Chat:
        raise NotImplementedError

    async def a_get_chat(self) -> Chat:
        raise NotImplementedError

    def get_dialog(self) -> str:
        raise NotImplementedError

    async def a_get_dialog(self) -> str:
        raise NotImplementedError

    def set_dialog(self, name: str):
        raise NotImplementedError

    async def a_set_dialog(self, name: str):
        raise NotImplementedError

    def get_next_step(self) -> str:
        raise NotImplementedError

    async def a_get_next_step(self) -> str:
        raise NotImplementedError

    def set_next_step(self, next_step: str="start"):
        raise NotImplementedError

    async def a_set_next_step(self, next_step: str="start"):
        raise NotImplementedError

    def get_history(self, after_date: (datetime, None)=None, before_date: (datetime, None)=None,
                    input: (bool, None)=None, text: (str, None)=None):
        raise NotImplementedError

    async def a_get_history(self, after_date: (datetime, None)=None,
                            before_date: (datetime, None)=None, input: (bool, None)=None,
                            text: (str, None)=None):
        raise NotImplementedError

    def add_history(self, date: datetime, text: (str, None)=None, images: Iterable[Image]=[],
                    audios: Iterable[Audio]=[], videos: Iterable[Video]=[],
                    documents: Iterable[Document]=[], locations: Iterable[Location]=[],
                    raw: Any=None, input: bool=True):
        raise NotImplementedError

    async def a_add_history(self, date: datetime, text: (str, None)=None,
                            images: Iterable[Image]=[], audios: Iterable[Audio]=[],
                            videos: Iterable[Video]=[], documents: Iterable[Document]=[],
                            locations: Iterable[Location]=[], raw: Any=None, input: bool=True):
        raise NotImplementedError

    def clear_history(self, after_date: (datetime, None)=None, before_date: (datetime, None)=None,
                      input: (bool, None)=None, text: (str, None)=None):
        raise NotImplementedError

    async def a_clear_history(self, after_date: (datetime, None)=None,
                              before_date: (datetime, None)=None, input: (bool, None)=None,
                              text: (str, None)=None):
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
    def connect(cls, **settings):
        raise NotImplementedError

    @classmethod
    async def a_connect(cls, **settings):
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
