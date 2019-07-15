import json
from botovod.agents import Agent, Audio, Chat, Document, Keyboard, Location, Image, Message, Video
from botovod.utils.exceptions import NotPassed
import logging
from typing import Any, Callable, Iterator


class Dialog:
    def __init__(self, agent: Agent, chat: Chat, message: Message):
        self.agent = agent
        self.chat = chat
        self.message = message
        self.follower = agent.botovod.dbdriver.get_follower(agent, chat)
        if self.follower is None:
            self.follower = agent.botovod.dbdriver.add_follower(agent, chat)

    def __new__(cls, agent: Agent, chat: Chat, message: Message):
        dialog = super().__new__(cls)
        dialog.__init__(agent, chat, message)

        dialog_name = dialog.follower.get_dialog()
        if dialog_name is not None and dialog_name != cls.__name__:
            raise NotPassed
        
        if dialog_name is None:
            dialog.follower.set_dialog(cls.__name__)
        next_step = dialog.follower.get_next_step()
        if next_step:
            getattr(dialog, next_step)()
        else:
            return dialog.start()

    def reply(self, text: (str, None)=None, images: Iterator[Image]=[],
              audios: Iterator[Audio]=[], documents: Iterator[Document]=[],
              videos: Iterator[Video]=[], locations: Iterator[Location]=[],
              keyboard: (Keyboard, None)=None, raw: Any=None):
        self.agent.send_message(self.chat, text=text, images=images, audios=audios,
                                documents=documents, videos=videos, locations=locations,
                                keyboard=keyboard, raw=raw)

    async def a_reply(self, text: (str, None)=None, images: Iterator[Image]=[],
                      audios: Iterator[Audio]=[], documents: Iterator[Document]=[],
                      videos: Iterator[Video]=[], locations: Iterator[Location]=[],
                      keyboard: (Keyboard, None)=None, raw: Any=None):
        await self.agent.a_send_message(self.chat, text=text, images=images, audios=audios,
                                        documents=documents, videos=videos, locations=locations,
                                        keyboard=keyboard, raw=raw)

    def set_next_step(self, function: Callable):
        if hasattr(function, "__self__"):
            self.follower.set_dialog(function.__self__.__class__.__name__)
        else:
            self.follower.set_dialog(function.__qualname__.split(".")[-2])
        self.follower.set_next_step(function.__name__)

    async def a_set_next_step(self, function: Callable):
        if hasattr(function, "__self__"):
            await self.follower.a_set_dialog(function.__self__.__class__.__name__)
        else:
            await self.follower.a_set_dialog(function.__qualname__.split(".")[-2])
        await self.follower.a_set_next_step(function.__name__)

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
