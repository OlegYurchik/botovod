from . import utils



class Botovod:
    def __init__(self, settings: dict):
        self.agents = dict()
        self.handlers = list()
        for setting in settings:
            module = __import__(setting["agent"], fromlist=["Agent"])
            if setting["name"] in self.agents:
                raise AlreadyExistsError("Agent with name '%s' already exists" % setting["name"])
            agent = module.Agent(manager=self, name=setting["name"], **setting["settings"])
            self.agents[setting["name"]] = agent

    def add_handler(self, handler: callable):
        self.handlers.append(handler)

    def start(self, name=None):
        if not name is None:
            self.agents[name].start()
            return
        for agent in self.agents.values():
            agent.start()

    def stop(self, name=None):
        if not name is None:
            self.agents[name].stop()
            return
        for agent in self.agents.values():
            agent.stop()
    
    def listen(self, name, headers: dict, body: str) -> dict:
        agent = self.agents[name]
        return agent.listen(headers, body)


class Agent:
    def __init__(self, manager: Botovod, name: str):
        self.manager = manager
        self.name = name
    
    def listen(self, headers: dict, body: str) -> dict:
        messages = self.parser(None, headers, body)
        for chat, message in messages.items():
            for handler in self.manager.handlers:
                try:
                    handler(self, chat, message)
                except utils.NotPassed as e:
                    continue
                break
        status, headers, body = self.responser()
        return {"status": status, "headers": headers, "body": body}
    
    def start(self):
        raise NotImplementedError
    
    def stop(self):
        raise NotImplementedError
    
    def parser(self, status: int, headers: dict, body: str):
        raise NotImplementedError
    
    def responser(self):
        raise NotImplementedError
    
    def send_message(self, chat: Chat, message: Message, **args):
        raise NotImplementedError


class Entity:
    def __init__(self):
        self.raw = dict()


class Chat(Entity):
    def __init__(self, agent: Agent, id):
        self.agent = agent.__class__
        self.id = id


class Message(Entity):
    def __init__(self):
        self.text = None
        self.images = []
        self.audios = []
        self.videos = []
        self.documents = []
        self.locations = []
        self.date = None
        self.raw = dict()


class Attachment(Entity):
    url = None
    file = None
        

class Image(Attachment):
    pass


class Audio(Attachment):
    pass


class Video(Attachment):
    pass


class Document(Attachment):
    pass


class Location(Entity):
    def __init__(self, latitude: float, longitude: float):
        self.latitude = latitude
        self.longitude = longitude
