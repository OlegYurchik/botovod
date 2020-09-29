class BotovodException(Exception):
    pass


class AgentException(BotovodException):
    pass


class AgentNotExistException(BotovodException):
    def __init__(self, name: str):
        super().__init__(f"Botovod have not '{name}' agent")
        self.name = name


class HandlerNotPassed(BotovodException):
    def __init__(self):
        super().__init__("Handler not passed")
