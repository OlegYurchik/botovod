class BotovodException(Exception):
    pass


class AgentNotExist(BotovodException):
    def __init__(self, agent_name: str):

        super().__init__(f"Botovod have not '{agent_name}' agent")
        self.agent_name = agent_name


class HandlerNotPassed(BotovodException):
    def __init__(self):

        super().__init__("Handler not passed")
