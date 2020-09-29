from typing import Callable, Iterator, Optional

from .agents import Agent, Attachment, Chat, Keyboard, Location, Message
from .dbdrivers import Follower
from .exceptions import HandlerNotPassed


class Dialog:
    def __init__(self, agent: Agent, chat: Chat, message: Message,
                 follower: Follower):
        self.agent = agent
        self.chat = chat
        self.message = message
        self.follower = follower

    def __new__(cls, agent: Agent, chat: Chat, message: Message,
                follower: Follower):
        dialog = super().__new__(cls)
        dialog.__init__(agent=agent, chat=chat, message=message, follower=follower)

        return dialog.process()

    def process(self):
        dialog_name = self.follower.get_dialog()
        if dialog_name is not None and dialog_name != self.__class__.__name__:
            raise HandlerNotPassed

        if dialog_name is None:
            self.follower.set_dialog(self.__class__.__name__)
        next_step = self.follower.get_next_step()
        if next_step:
            getattr(self, next_step)()
        else:
            return self.start()

    def reply(self, text: Optional[str] = None, images: Iterator[Attachment] = (),
              audios: Iterator[Attachment] = (), documents: Iterator[Attachment] = (),
              videos: Iterator[Attachment] = (), locations: Iterator[Location] = (),
              keyboard: Optional[Keyboard] = None, **raw):
        self.agent.send_message(
            self.chat,
            text=text,
            images=images,
            audios=audios,
            documents=documents,
            videos=videos,
            locations=locations,
            keyboard=keyboard,
            **raw,
        )

    def set_next_step(self, function: Callable):
        if hasattr(function, "__self__"):
            name = function.__self__.__class__.__name__
        else:
            name = function.__qualname__.split(".")[-2]
        self.follower.set_dialog(name)
        self.follower.set_next_step(function.__name__)

    def start_dialog(self, dialog_class: Callable):
        self.follower.set_dialog(dialog_class.__name__)
        dialog_class(self.agent, self.chat, self.message, self.follower)

    def start(self):
        raise NotImplementedError


class AsyncDialog(Dialog):
    async def process(self):
        dialog_name = await self.follower.a_get_dialog()
        if dialog_name is not None and dialog_name != self.__class__.__name__:
            raise HandlerNotPassed

        next_step = "start"
        if dialog_name is None:
            await self.follower.a_set_dialog(self.__class__.__name__)
        else:
            next_step = await self.follower.a_get_next_step()
        if next_step:
            await getattr(self, next_step)()
        else:
            return await self.start()

    async def reply(self, text: Optional[str] = None, images: Iterator[Attachment] = (),
                    audios: Iterator[Attachment] = (), documents: Iterator[Attachment] = (),
                    videos: Iterator[Attachment] = (), locations: Iterator[Location] = (),
                    keyboard: Optional[Keyboard] = None, **raw):
        return await self.agent.a_send_message(
            chat=self.chat,
            text=text,
            images=images,
            audios=audios,
            documents=documents,
            videos=videos,
            locations=locations,
            keyboard=keyboard,
            **raw,
        )

    async def set_next_step(self, function: Callable):
        if hasattr(function, "__self__"):
            await self.follower.a_set_dialog(function.__self__.__class__.__name__)
        else:
            await self.follower.a_set_dialog(function.__qualname__.split(".")[-2])
        await self.follower.a_set_next_step(function.__name__)

    async def start_dialog(self, dialog_class: Callable):
        await self.follower.a_set_dialog(dialog_class.__name__)
        await dialog_class(self.agent, self.chat, self.message, self.follower)

    async def start(self):
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
