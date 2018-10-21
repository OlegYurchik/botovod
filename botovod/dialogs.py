from utils import NotPassed


class Dialog:
    def __init__(self, name, dbdriver):
        self.name = name
        self._dbdriver = dbdriver

    def __call__(self, agent, chat, message):
        follower = self._dbdriver.get_follower(agent, chat)
        if follower is None:
            follower = self._dbdriver.add_follower(agent, chat)
        dialog_name = follower.get_dialog_name()
        if not dialog_name is None and dialog_name != self.name:
            raise NotPassed
        next_step = follower.get_next_step()
        if next_step:
            getattr(self, next_step)(agent, follower, message)
        else:
            self.start(agent, follower, message)

    def start(self, agent, follower, message):
        raise NotImplementedError
