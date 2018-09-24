class Follower:
    def __init__(self, agent, chat, driver):
        self.chat = chat
        self.driver = driver
        self.dialog = None
        self.settings = None

class Dialog:
    def __init__(self, cache_driver):
        self._cache = cache_driver

    @staticmethod
    def handler(agent, chat, message):
        pass