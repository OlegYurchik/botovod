import json
from botovod import Keyboard
from botovod.utils import NotPassed
import logging


class Dialog:
    def __init__(self, dbdriver_class, logger: logging.Logger=logging.getLogger()):
        self._dbdriver = dbdriver_class
        self.logger = logger
    
    def __call__(self, agent, chat, message):
        self.agent = agent
        self.chat = chat
        self.message = message
        self.follower = self._dbdriver.get_follower(agent, chat)
        if self.follower is None:
            self.follower = self._dbdriver.add_follower(agent, chat)
        dialog_name = self.follower.get_dialog_name()
        if not dialog_name is None and dialog_name != self.__class__.__name__:
            self.logger.info("Dialog '%s' not passed, skipping...", self.__class__.__name__)
            raise NotPassed
        self.logger.info("Dialog '%s' passed", self.__class__.__name__)
        if dialog_name is None:
            self.follower.set_dialog_name(self.__class__.__name__)
        next_step = self.follower.get_next_step()
        if next_step:
            getattr(self, next_step)()
        else:
            self.start()

    def start_new_dialog(self, cls):
        self.set_next_dialog(cls)
        self.set_next_step("start")
        dialog = cls(self._dbdriver)
        dialog(self.agent, self.chat, self.message)

    def set_next_dialog(self, cls):
        self.logger.info("Set next dialog '%s'", cls.__name__)
        self.follower.set_dialog_name(cls.__name__)

    def set_next_step(self, name):
        self.logger.info("Set next step '%s'", name)
        self.follower.set_next_step(name)
    
    def reply(self, message):
        self.agent.send_message(self.chat, message)

    def start(self):
        raise NotImplementedError


class MessagePaginator(Dialog):
    @property
    def prev_button(self) -> str:
        raise NotImplementedError
    
    @property
    def next_button(self) -> str:
        raise NotImplementedError


class KeyboardPaginator(Dialog):
    @property
    def limit(self) -> int:
        raise NotImplementedError
    
    @property
    def prev_button(self) -> str:
        raise NotImplementedError
    
    @property
    def next_button(self) -> str:
        raise NotImplementedError

    def start(self):
        self.follower.set_value("page", 0)
        data = self.get_all_data()
        if not data:
            self.action_no_data()
            return
        
        page_data = data[:self.limit]
        message = self.render(page_data)
        buttons = []
        if not message.keyboard is None:
            buttons.extend(message.keyboard.buttons)
        if self.limit < len(data):
            buttons.append(self.next_button)
        message.keyboard = Keyboard(*buttons)
        self.reply(message)

        self.set_next_step("handle")

    def handle(self):
        page = self.follower.get_value("page")
        if page is None:
            page = 0
        data = self.get_all_data()
        if not data:
            self.action_no_data()
            return
        
        if self.message.text == self.next_button:
            if page*self.limit < len(data): 
                page += 1
        elif self.message.text == self.prev_button:
            if page > 0:
                page -= 1
        else:
            page_data = data[page*self.limit:(page+1)*self.limit]
            self.action(page_data)
            return

        page_data = data[page*self.limit:(page+1)*self.limit]
        message = self.render(page_data)
        buttons = []
        if not message.keyboard is None:
            buttons.extend(message.keyboards.buttons)
        if page > 0:
            buttons.append(self.prev_button)
        if (page+1)*self.limit < len(data):
            buttons.append(self.next_button)
        message.keyboard = Keyboard(*buttons)

        self.agent.send_message(self.chat, message)
        self.follower.set_value("page", page)

    def get_all_data(self):
        raise NotImplementedError

    def render(self, data) -> "Message":
        raise NotImplementedError

    def action(self, data):
        raise NotImplementedError

    def action_no_data(self):
        raise NotImplementedError
