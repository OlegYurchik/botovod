from .agents import Agent
from .dbdrivers import DBDriver 
from .exceptions import AgentNotExist
import asyncio
from collections import OrderedDict
from typing import Callable, Dict, Optional, Tuple


class Botovod:
    def __init__(self, dbdriver: Optional[DBDriver]=None):

        self.dbdriver = dbdriver

        self._agents = {}
        self._handlers = OrderedDict()
        self._items = {}

    def __setitem__(self, name: str, value):

        self._items[name] = value

    def __getitem__(self, name: str):

        return self._items[name]

    def __delitem__(self, name: str):

        del self._items[name]

    def get(self, name: str):

        return self._items.get(name)

    def add_handlers(self, **handlers: Dict[str, Callable]):

        self._handlers.update(handlers)

    def add_handler(self, name: str, handler: Callable):

        self._handlers[name] = handler

    def get_handler(self, name: str):

        return self._handlers.get(name)

    def remove_handler(self, name: str):

        del self._handlers[name]

    def add_agents(self, **agents: Dict[str, Agent]):

        self._agents.update(agents)
        for agent in agents.values():
            agent.botovod = self

    def add_agent(self, name: str, agent: Agent):

        self._agents[name] = agent
        agent.botovod = self

    def get_agent(self, name: str):

        return self._agents[name]

    def remove_agent(self, name: str):

        agent = self._agents[name]
        agent.botovod = None
        del self._agents[name]

    def start(self):

        for agent in self._agents.values():
            agent.start()

    async def a_start(self):

        for agent in self._agents.values():
            await agent.a_start()

    def stop(self):

        for agent in self._agents.values():
            agent.stop()

    async def a_stop(self):

        for agent in self._agents.values():
            await agent.a_sstop()

    def listen(self, name: str, headers: Dict[str, str],
               body: str) -> Optional[Tuple[int, Dict[str, str], str]]:

        if name is not None and name not in self._agents:
            raise AgentNotExist(name)

        return self._agents[name].listen(headers, body)

    async def a_listen(self, name: str, headers: Dict[str, str],
                       body: str) -> (Tuple[int, Dict[str, str], str], None):

        if name is not None and name not in self._agents:
            raise AgentNotExist(name)

        return await self._agents[name].alisten(headers, body)
