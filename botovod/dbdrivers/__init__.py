class Follower:
    def get_chat(self):
        raise NotImplementedError

    def get_dialog_name(self):
        raise NotImplementedError
    
    def set_dialog_name(self, name):
        raise NotImplementedError

    def get_next_step(self) -> str:
        raise NotImplementedError
    
    def set_next_step(self, next_step="start"):
        raise NotImplementedError

    def get_history(self, after_date=None, before_date=None, input=None, text=None):
        raise NotImplementedError

    def add_history(self, message):
        raise NotImplementedError

    def clear_history(self, after_date=None, before_date=None, input=None, text=None):
        raise NotImplementedError

    def get_value(self, name: str) -> str:
        raise NotImplementedError
    
    def set_value(self, name: str, value: str):
        raise NotImplementedError

    def delete_value(self, name: str):
        raise NotImplementedError


class DBDriver:
    def __init__(self, **settings):
        self.connect(**settings)
    
    def connect(self, **settings):
        raise NotImplementedError

    def get_follower(self, agent, chat):
        raise NotImplementedError
    
    def add_follower(self, agent, chat):
        raise NotImplementedError
    
    def delete_follower(self, agent, chat):
        raise NotImplementedError
