import json
from botovod.agents import Agent, Chat, Keyboard, Message
from botovod.utils.exceptions import NotPassed
import logging


class Dialog:
    def __new__(cls, agent: Agent, chat: Chat, message: Message):
        if agent.botovod is None or agent.botovod.dbdriver is None:
            return

        dialog = super().__new__(cls)
        dialog.agent = agent
        dialog.chat = chat
        dialog.message = message
        dialog.follower = agent.botovod.dbdriver.get_follower(agent, chat)
        if dialog.follower is None:
            dialog.follower = agent.botovod.dbdriver.add_follower(agent, chat)

        dialog_name = dialog.follower.get_dialog_name()
        if dialog_name is not None and dialog_name != cls.__name__:
            raise NotPassed
        
        if dialog_name is None:
            dialog.follower.set_dialog_name(cls.__name__)
        next_step = dialog.follower.get_next_step()
        if next_step:
            getattr(dialog, next_step)()
        else:
            dialog.start()

    @property
    def logger(self):
        raise NotImplementedError

    def start(self):
        raise NotImplementedError


# class MessagePaginator(Dialog):
#     @property
#     def prev_button(self) -> str:
#         raise NotImplementedError
    
#     @property
#     def next_button(self) -> str:
#         raise NotImplementedError


# class KeyboardPaginator(Dialog):
#     @property
#     def limit(self) -> int:
#         raise NotImplementedError
    
#     @property
#     def prev_button(self) -> str:
#         raise NotImplementedError
    
#     @property
#     def next_button(self) -> str:
#         raise NotImplementedError

#     def start(self):
#         self.follower.set_value("page", 0)
#         data = self.get_all_data()
#         if not data:
#             self.action_no_data()
#             return
        
#         page_data = data[:self.limit]
#         message = self.render(page_data)
#         buttons = []
#         if not message.keyboard is None:
#             buttons.extend(message.keyboard.buttons)
#         if self.limit < len(data):
#             buttons.append(self.next_button)
#         message.keyboard = Keyboard(*buttons)
#         self.reply(message)

#         self.follower.set_next_step("handle")

#     def handle(self):
#         page = self.follower.get_value("page")
#         if page is None:
#             page = 0
#         data = self.get_all_data()
#         if not data:
#             self.action_no_data()
#             return
        
#         if self.message.text == self.next_button:
#             if page*self.limit < len(data): 
#                 page += 1
#         elif self.message.text == self.prev_button:
#             if page > 0:
#                 page -= 1
#         else:
#             page_data = data[page*self.limit:(page+1)*self.limit]
#             self.action(page_data)
#             return

#         page_data = data[page*self.limit:(page+1)*self.limit]
#         message = self.render(page_data)
#         buttons = []
#         if not message.keyboard is None:
#             buttons.extend(message.keyboards.buttons)
#         if page > 0:
#             buttons.append(self.prev_button)
#         if (page+1)*self.limit < len(data):
#             buttons.append(self.next_button)
#         message.keyboard = Keyboard(*buttons)

#         self.agent.send_message(self.chat, message)
#         self.follower.set_value("page", page)

#     def get_all_data(self):
#         raise NotImplementedError

#     def render(self):
#         raise NotImplementedError

#     @classmethod
#     def action(cls):
#         raise NotImplementedError

#     @classmethod
#     def action_no_data(cls):
#         raise NotImplementedError
