from __future__ import annotations
from botovod.agents import Agent
import logging


class AgentDict(dict):
    def __init__(self, botovod: Botovod):
        self.botovod = botovod

    def __setitem__(self, key: str, value: Agent):
        if key in self:
            self[key].set_botovod(None)
        value.botovod = self.botovod
        value.name = key
        return super().__setitem__(key, value)

    def __delitem__(self, key: str):
        self[key].botovod = None
        self[key].name = None
        return super().__delitem__(key)


class Botovod:
    def __init__(self, logger: logging.Logger=logging.getLogger(__name__)):
        self.agents = AgentDict(self)
        self.handlers = []
        self.logger = logger

        logger.info("Initialiaze Botovod manager")

    def start(self, name=None):
        if not name is None and name not in self.agents:
            self.logger.error("Botovod have no agent with name '%s'", name)
            return
        agents = self.agents if name is None else {name: self.agents[name]}
        for name, agent in agents.items():
            self.logger.info("Botovod starting allagent '%s' with name '%s'", agents[name], name)
            agent.start()

    def stop(self, name=None):
        if not name is None and name not in self.agents:
            self.logger.error("Botovod have no agent with name '%s'", name)
            return
        agents = self.agents if name is None else {name: self.agents[name]}
        for name, agent in agents.items():
            self.logger.info("Botovod stoping allagent '%s' with name '%s'", agents[name], name)
            agent.stop()

    def listen(self, name: str, headers: dict, body: str) -> dict:
        agent = self.agents[name]
        return agent.listen(headers, body)
