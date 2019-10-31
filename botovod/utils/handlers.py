from ..agents import Agent, Chat, Message
from ..agents.telegram import TelegramAgent, TelegramCallback
from ..dbdrivers import Follower
from ..dialogs import AsyncDialog, Dialog
from ..exceptions import HandlerNotPassed
from functools import wraps
import re
from typing import Callable, Optional


def to_text(is_dialog: bool=False):
    def decorator(func: Callable):
        @wraps(func)
        def func_wrapper(agent: Agent, chat: Chat, message: Message,
                         follower: Optional[Follower]=None, *args, **kwargs):

            if message.text is None:
                raise HandlerNotPassed

            return func(agent, chat, message.text, follower, *args, **kwargs)

        @wraps(func)
        def dialog_wrapper(self, *args, **kwargs):

            if self.message.text is None:
                raise HandlerNotPassed

            return func(self, self.message.text, *args, **kwargs)

        return dialog_wrapper if is_dialog else func_wrapper

    return decorator


def to_attachments(is_dialog: bool=False):
    def decorator(func: Callable):
        @wraps(func)
        def func_wrapper(agent: Agent, chat: Chat, message: Message,
                         follower: Optional[Follower]=None, *args, **kwargs):

            attachments = []
            attachments.extend(message.images)
            attachments.extend(message.audios)
            attachments.extend(message.videos)
            attachments.extend(message.documents)
            if not attachments:
                raise HandlerNotPassed

            return func(agent, chat, attachments, follower, *args, **kwargs)

        @wraps(func)
        def dialog_wrapper(self, *args, **kwargs):

            attachments = []
            attachments.extend(self.message.images)
            attachments.extend(self.message.audios)
            attachments.extend(self.message.videos)
            attachments.extend(self.message.documents)
            if not attachments:
                raise HandlerNotPassed

            return func(self, attachments, *args, **kwargs)

        return dialog_wrapper if is_dialog else func_wrapper

    return decorator


def to_images(is_dialog: bool=False):
    def decorator(func: Callable):
        @wraps(func)
        def func_wrapper(agent: Agent, chat: Chat, message: Message,
                         follower: Optional[Follower]=None, *args, **kwargs):

            if not message.images:
                raise HandlerNotPassed

            return func(agent, chat, message.images, follower, *args, **kwargs)

        @wraps(func)
        def dialog_wrapper(self, *args, **kwargs):

            if not self.message.images:
                raise HandlerNotPassed

            return func(self, self.message.images, *args, **kwargs)

        return dialog_wrapper if is_dialog else func_wrapper

    return decorator


def to_audios(is_dialog: bool=False):
    def decorator(func: Callable):
        @wraps(func)
        def func_wrapper(agent: Agent, chat: Chat, message: Message,
                         follower: Optional[Follower]=None, *args, **kwargs):

            if not message.audios:
                raise HandlerNotPassed

            return func(agent, chat, message.audios, *args, **kwargs)

        @wraps(func)
        def dialog_wrapper(self, *args, **kwargs):

            if not self.message.audios:
                raise HandlerNotPassed

            return func(self, self.message.audios, *args, **kwargs)

        return dialog_wrapper if is_dialog else func_wrapper

    return decorator


def to_videos(is_dialog: bool=False):
    def decorator(func: Callable):
        @wraps(func)
        def func_wrapper(agent: Agent, chat: Chat, message: Message,
                         follower: Optional[Follower]=None, *args, **kwargs):

            if not message.videos:
                raise HandlerNotPassed

            return func(agent, chat, message.videos, *args, **kwargs)

        @wraps(func)
        def dialog_wrapper(self, *args, **kwargs):

            if not self.message.videos:
                raise HandlerNotPassed

            return func(self, self.message.videos, *args, **kwargs)

        return dialog_wrapper if is_dialog else func_wrapper

    return decorator


def to_documents(is_dialog: bool=False):
    def decorator(func: Callable):
        @wraps(func)
        def func_wrapper(agent: Agent, chat: Chat, message: Message,
                         follower: Optional[Follower]=None, *args, **kwargs):

            if not message.documents:
                raise HandlerNotPassed

            return func(agent, chat, message.documents, follower, *args, **kwargs)

        @wraps(func)
        def dialog_wrapper(self, *args, **kwargs):

            if not self.message.documents:
                raise HandlerNotPassed

            return func(self, self.message.documents, *args, **kwargs)

        return dialog_wrapper if is_dialog else func_wrapper

    return decorator


def to_locations(is_dialog: bool=False):
    def decorator(func: Callable):
        @wraps(func)
        def func_wrapper(agent: Agent, chat: Chat, message: Message,
                         follower: Optional[Follower]=None, *args, **kwargs):

            if not message.locations:
                raise HandlerNotPassed

            return func(agent, chat, message.locations, *args, **kwargs)

        @wraps(func)
        def dialog_wrapper(self, *args, **kwargs):

            if not self.message.locations:
                raise HandlerNotPassed

            return func(self, self.message.locations, *args, **kwargs)

        return dialog_wrapper if is_dialog else func_wrapper

    return decorator


def only_regexp(expression: str, is_dialog: bool=False):
    def decorator(func: Callable):
        @wraps(func)
        def func_wrapper(agent: Agent, chat: Chat, message: Message,
                         follower: Optional[Follower]=None, *args, **kwargs):

            if message.text is None:
                raise HandlerNotPassed
            match = re.match(expression, message.text)
            if not match:
                raise HandlerNotPassed

            return func(agent, chat, *match.groups(), follower, *args, **kwargs)

        @wraps(func)
        def dialog_wrapper(self, *args, **kwargs):

            if self.message.text is None:
                raise HandlerNotPassed
            match = re.match(expression, self.message.text)
            if not match:
                raise HandlerNotPassed

            return func(self, *match.groups(), *args, **kwargs)

        return dialog_wrapper if is_dialog else func_wrapper

    return decorator


def only_agent(name: str, is_dialog: bool=False):
    def decorator(func: Callable):
        @wraps(func)
        def func_wrapper(agent: Agent, chat: Chat, message: Message,
                         follower: Optional[Follower]=None, *args, **kwargs):

            if agent.name != name:
                raise HandlerNotPassed

            return func(agent, chat, message, follower, *args, **kwargs)

        @wraps(func)
        def dialog_wrapper(self, *args, **kwargs):

            if self.agent.name != name:
                raise HandlerNotPassed

            return func(self, *args, **kwargs)

        return dialog_wrapper if is_dialog else func_wrapper

    return decorator


def only_chat(chat: Chat, cls: Agent=Agent, is_dialog: bool=False):
    def decorator(func: Callable):
        @wraps(func)
        def func_wrapper(agent: Agent, chat: Chat, message: Message,
                         follower: Optional[Follower]=None, *args, **kwargs):

            if not issubclass(agent, cls):
                raise HandlerNotPassed
            if message.chat.id != chat:
                raise HandlerNotPassed

            return func(agent, chat, message, follower, *args, **kwargs)

        @wraps(func)
        def dialog_wrapper(self, *args, **kwargs):

            if not issubclass(self.agent, cls):
                raise HandlerNotPassed
            if self.message.chat.id != chat:
                raise HandlerNotPassed

            return func(self, *args, **kwargs)

        return dialog_wrapper if is_dialog else func_wrapper

    return decorator


def only_telegram_callback(is_dialog: bool=False):
    def decorator(func: Callable):
        @wraps(func)
        def func_wrapper(agent: Agent, chat: Chat, message: Message,
                         follower: Optional[Follower]=None, *args, **kwargs):

            if isinstance(agent, TelegramAgent) and isinstance(message, TelegramCallback):
                return func(agent, chat, message, follower, *args, **kwargs)

            raise HandlerNotPassed

        @wraps(func)
        def dialog_wrapper(self, *args, **kwargs):

            if isinstance(self.agent, TelegramAgent) and isinstance(self.message, TelegramCallback):
                return func(self, self.message.text, *args, **kwargs)

            raise HandlerNotPassed

        return dialog_wrapper if is_dialog else func_wrapper

    return decorator


def start_dialog(dialog_cls: Dialog, agent: Agent, chat: Chat, message: Message,
                 follower: Follower):

    follower.set_dialog(dialog_cls.__name__)
    return dialog_cls(agent, chat, message, follower)


async def start_async_dialog(dialog_cls: AsyncDialog, agent: Agent, chat: Chat, message: Message,
                             follower: Follower):

    await follower.a_set_dialog(dialog_cls.__name__)
    return await dialog_cls(agent, chat, message, follower)
