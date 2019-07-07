from __future__ import annotations
from botovod.agents import Agent
import logging


class AgentDict(dict):
    def __init__(self, botovod: Botovod):
        self.botovod = botovod

    def __setitem__(self, key: str, value: Agent):
        if key in self:
            del self[key]
        value.botovod = self.botovod
        value.name = key

        self.botovod.logger.info("[%s:%s] Agent was added to Botovod.", value, key)
        return super().__setitem__(key, value)

    def __delitem__(self, key: str):
        self[key].botovod = None
        self[key].name = None

        self.botovod.logger.info("[%s:%s] Agent was removed from Botovod.", self[key], key)
        return super().__delitem__(key)


class Botovod:
    def __init__(self, logger: logging.Logger=logging.getLogger(__name__)):
        self.agents = AgentDict(self)
        self.handlers = []
        self.logger = logger

        logger.info("Initialiaze Botovod.")

    def start(self):
        for agent in self.agents.values():
            agent.start()

    def stop(self):
        for agent in self.agents.values():
            agent.stop()

    def listen(self, name: str, headers: dict, body: str) -> dict:
        if name is not None and name not in self.agents:
            self.logger.error("Botovod have no agent with name '%s'!", name)
            return
        return self.agents[name].listen(headers, body)
