from typing import Callable, Dict, Iterable, Optional, Tuple

from .agents import Agent
from .dbdrivers import DBDriver 
from .exceptions import AgentNotExistException


class Botovod:
    def __init__(self, dbdriver: Optional[DBDriver] = None):
        self._dbdriver = dbdriver
        self._agents = {}
        self._handlers = []
        self._items = {}

    def __setitem__(self, name: str, value):
        self._items[name] = value

    def __getitem__(self, name: str):
        return self._items[name]

    def __delitem__(self, name: str):
        del self._items[name]

    @property
    def dbdriver(self):
        return self._dbdriver

    @property
    def handlers(self):
        return self._handlers.copy()

    def get(self, name: str, default=None):
        return self._items.get(name, default)

    def add_handlers(self, *handlers: Iterable[Callable]):
        self._handlers.extend(handlers)

    def add_handler(self, handler: Callable):
        self._handlers.append(handler)

    def remove_handler(self, handler: Callable):
        for index in range(len(self._handlers)):
            if self._handlers[index] is handler:
                del self._handlers[index]
                break

    def clear_handlers(self):
        self._handlers.clear()

    @property
    def agents(self):
        return self._agents.values()

    def add_agents(self, **agents: Dict[str, Agent]):
        self._agents.update(agents)
        for name, agent in agents.items():
            if agent.botovod is not None:
                agent.botovod.remove_agent(name)
            agent.botovod = self
            agent.name = name

    def add_agent(self, name: str, agent: Agent):
        self._agents[name] = agent
        if agent.botovod is not None:
            agent.botovod.remove_agent(name)
        agent.botovod = self
        agent.name = name

    def get_agent(self, name: str):
        return self._agents.get(name)

    def remove_agent(self, name: str):
        agent = self._agents.get(name)
        if agent is None:
            return
        agent.botovod = None
        agent.name = None
        del self._agents[name]

    def start(self):
        for agent in self._agents.values():
            if not agent.running:
                agent.start()

    async def a_start(self):
        for agent in self._agents.values():
            if not agent.running:
                await agent.a_start()

    def stop(self):
        for agent in self._agents.values():
            if agent.running:
                agent.stop()

    async def a_stop(self):
        for agent in self._agents.values():
            if agent.running:
                await agent.a_stop()

    def listen(self, name: str, headers: Dict[str, str],
               body: str) -> Optional[Tuple[int, Dict[str, str], str]]:
        if name not in self._agents:
            raise AgentNotExistException(name)

        return self._agents[name].listen(headers, body, **self._items)

    async def a_listen(self, name: str, headers: Dict[str, str],
                       body: str) -> (Tuple[int, Dict[str, str], str], None):
        if name not in self._agents:
            raise AgentNotExistException(name)

        return await self._agents[name].a_listen(headers, body, **self._items)
