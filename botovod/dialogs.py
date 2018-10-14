class DialogHandler:
    def __init__(self, dbdriver):
        self._dbdriver = dbdriver

    def __call__(self, agent, chat, message):
        follower = self._dbdriver.get_follower(agent, chat)
        if follower is None:
            next_step = None
            follower = self._dbdriver.add_follower(agent, chat)
        if next_step:
            getattr(self, next_step)(agent, follower, message)
        self.start(agent, self.follower, message)

    def start(self, agent, follower, message):
        raise NotImplementedError
