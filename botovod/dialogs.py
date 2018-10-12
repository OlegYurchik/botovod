class DialogHandler:
    def __init__(self, dbdriver):
        self._dbdriver = dbdriver

    def handler(self, agent, chat, message):
        follower = self._dbdriver.get_follower(agent, chat)
        if follower is None:
            next_step = None
            follower = self._dbdriver.add_follower(agent, chat)
        if next_step:
            getattr(self, next_step)(follower, message)
        self.start(self.follower, message)
        
    def start(self, follower, message):
        raise NotImplementedError
