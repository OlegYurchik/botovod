import logging


class Agent:
    def __init__(self, logger: logging.Logger=logging.getLogger(__name__)):
        self.logger = logger
        self.botovod = None
        self.running = False

    def listen(self, headers: dict, body: str) -> dict:
        from botovod.utils.exceptions import NotPassed

        messages = self.parser(None, headers, body)
        print(messages)
        response = None
        for chat, message in messages:
            for handler in self.botovod.handlers:
                try:
                    response = handler(self, chat, message)
                except NotPassed:
                    continue
                break
        if not response is None:
            status, headers, body = response
        else:
            status, headers, body = self.responser(200, headers, body)
        return {"status": status, "headers": headers, "body": body}

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def parser(self, status: int, headers: dict, body: str):
        raise NotImplementedError

    def responser(self, status: int, headers: dict, body: str):
        raise NotImplementedError

    def send_message(self, chat, message, **args):
        raise NotImplementedError


class Entity:
    def __init__(self):
        self.raw = dict()


class Chat(Entity):
    def __init__(self, agent: str, id):
        self.agent = agent
        self.id = id


class Message(Entity):
    def __init__(self):
        self.text = None
        self.images = []
        self.audios = []
        self.videos = []
        self.documents = []
        self.locations = []
        self.keyboard = None
        self.date = None
        self.raw = dict()


class Attachment(Entity):
    url = None
    file = None


class Location(Entity):
    def __init__(self, latitude: float, longitude: float):
        self.latitude = latitude
        self.longitude = longitude


class Keyboard(Entity):
    def __init__(self, *buttons):
        self.buttons = buttons


class KeyboardButton(Entity):
    def __init__(self, text):
        self.text = text
