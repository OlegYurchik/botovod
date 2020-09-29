from __future__ import annotations
from botovod.agents import Agent, Chat
from typing import Dict, Optional


class Follower:
    def get_chat(self) -> Chat:
        raise NotImplementedError

    async def a_get_chat(self) -> Chat:
        raise NotImplementedError

    def get_dialog(self) -> Optional[str]:
        raise NotImplementedError

    async def a_get_dialog(self) -> Optional[str]:
        raise NotImplementedError

    def set_dialog(self, name: Optional[str] = None):
        raise NotImplementedError

    async def a_set_dialog(self, name: Optional[str] = None):
        raise NotImplementedError

    def get_next_step(self) -> Optional[str]:
        raise NotImplementedError

    async def a_get_next_step(self) -> Optional[str]:
        raise NotImplementedError

    def set_next_step(self, next_step: Optional[str] = None):
        raise NotImplementedError

    async def a_set_next_step(self, next_step: Optional[str] = None):
        raise NotImplementedError

    def get_values(self) -> Dict[str, str]:
        raise NotImplementedError

    async def a_get_values(self) -> Dict[str, str]:
        raise NotImplementedError

    def get_value(self, name: str, default: Optional[str] = None) -> Optional[str]:
        raise NotImplementedError

    async def a_get_value(self, name: str, default: Optional[str] = None) -> Optional[str]:
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
    def connect(self, **settings):
        raise NotImplementedError

    async def a_connect(self, **settings):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError

    async def a_close(self):
        raise NotImplementedError

    def get_follower(self, agent: Agent, chat: Chat) -> Optional[Follower]:
        raise NotImplementedError

    async def a_get_follower(self, agent: Agent, chat: Chat) -> Optional[Follower]:
        raise NotImplementedError

    def add_follower(self, agent: Agent, chat: Chat) -> Follower:
        raise NotImplementedError

    async def a_add_follower(self, agent: Agent, chat: Chat) -> Follower:
        raise NotImplementedError

    def delete(self, follower: Follower):
        raise NotImplementedError

    async def a_delete(self, follower: Follower):
        raise NotImplementedError
