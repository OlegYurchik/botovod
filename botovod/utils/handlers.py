from botovod.agents import Agent, Chat, Message
from botovod.agents.telegram import TelegramAgent, TelegramCallback
from botovod.utils.exceptions import NotPassed
from functools import wraps
import re
from typing import Callable


def to_text(is_dialog: bool=False):
    def decorator(func: Callable):
        @wraps(func)
        def func_wrapper(agent: Agent, chat: Chat, message: Message):
            if message.text is None:
                raise NotPassed
            return func(agent, chat, message.text)

        @wraps(func)
        def dialog_wrapper(self):
            if self.message.text is None:
                raise NotPassed
            return func(self, self.message.text)

        return dialog_wrapper if is_dialog else func_wrapper

    return decorator


def to_attachments(is_dialog: bool=False):
    def decorator(func: Callable):
        @wraps(func)
        def func_wrapper(agent: Agent, chat: Chat, message: Message):
            attachments = []
            attachments.extend(message.images)
            attachments.extend(message.audios)
            attachments.extend(message.videos)
            attachments.extend(message.documents)
            if not attachments:
                raise NotPassed
            return func(agent, chat, attachments)

        @wraps(func)
        def dialog_wrapper(self):
            attachments = []
            attachments.extend(self.message.images)
            attachments.extend(self.message.audios)
            attachments.extend(self.message.videos)
            attachments.extend(self.message.documents)
            if not attachments:
                raise NotPassed
            return func(self, attachments)

        return dialog_wrapper if is_dialog else func_wrapper

    return decorator


def to_images(is_dialog: bool=False):
    def decorator(func: Callable):
        @wraps(func)
        def func_wrapper(agent: Agent, chat: Chat, message: Message):
            if not message.images:
                raise NotPassed
            return func(agent, chat, message.images)

        @wraps(func)
        def dialog_wrapper(self):
            if not self.message.images:
                raise NotPassed
            return func(self, self.message.images)

        return dialog_wrapper if is_dialog else func_wrapper

    return decorator


def to_audios(is_dialog: bool=False):
    def decorator(func: Callable):
        @wraps(func)
        def func_wrapper(agent: Agent, chat: Chat, message: Message):
            if not message.audios:
                raise NotPassed
            return func(agent, chat, message.audios)

        @wraps(func)
        def dialog_wrapper(self):
            if not self.message.audios:
                raise NotPassed
            return func(self, self.message.audios)

        return dialog_wrapper if is_dialog else func_wrapper

    return decorator


def to_videos(is_dialog: bool=False):
    def decorator(func: Callable):
        @wraps(func)
        def func_wrapper(agent: Agent, chat: Chat, message: Message):
            if not message.videos:
                raise NotPassed
            return func(agent, chat, message.videos)

        @wraps(func)
        def dialog_wrapper(self):
            if not self.message.videos:
                raise NotPassed
            return func(self, self.message.videos)

        return dialog_wrapper if is_dialog else func_wrapper

    return decorator


def to_documents(is_dialog: bool=False):
    def decorator(func: Callable):
        @wraps(func)
        def func_wrapper(agent: Agent, chat: Chat, message: Message):
            if not message.documents:
                raise NotPassed
            return func(agent, chat, message.documents)

        @wraps(func)
        def dialog_wrapper(self):
            if not self.message.documents:
                raise NotPassed
            return func(self, self.message.documents)

        return dialog_wrapper if is_dialog else func_wrapper

    return decorator


def to_locations(is_dialog: bool=False):
    def decorator(func: Callable):
        @wraps(func)
        def func_wrapper(agent: Agent, chat: Chat, message: Message):
            if not message.locations:
                raise NotPassed
            return func(agent, chat, message.locations)

        @wraps(func)
        def dialog_wrapper(self):
            if not self.message.locations:
                raise NotPassed
            return func(self, self.message.locations)

        return dialog_wrapper if is_dialog else func_wrapper

    return decorator


def only_regexp(expression: str, is_dialog: bool=False):
    def decorator(func: Callable):
        @wraps(func)
        def func_wrapper(agent: Agent, chat: Chat, message: Message):
            if message.text is None:
                raise NotPassed
            match = re.match(expression, message.text)
            if not match:
                raise NotPassed
            return func(agent, chat, *match.groups())

        @wraps(func)
        def dialog_wrapper(self):
            if self.message.text is None:
                raise NotPassed
            match = re.match(expression, self.message.text)
            if not match:
                raise NotPassed
            return func(self, *match.groups())

        return dialog_wrapper if is_dialog else func_wrapper

    return decorator


def only_agent(name: str, is_dialog: bool=False):
    def decorator(func: Callable):
        @wraps(func)
        def func_wrapper(agent: Agent, chat: Chat, message: Message):
            if agent.name != name:
                raise NotPassed
            return func(agent, chat, message)

        @wraps(func)
        def dialog_wrapper(self):
            if self.agent.name != name:
                raise NotPassed
            return func(self)

        return dialog_wrapper if is_dialog else func_wrapper

    return decorator


def only_chat(chat: Chat, cls: Agent=Agent, is_dialog: bool=False):
    def decorator(func: Callable):
        @wraps(func)
        def func_wrapper(agent: Agent, chat: Chat, message: Message):
            if not issubclass(agent, cls):
                raise NotPassed
            if message.chat.id != chat:
                raise NotPassed
            return func(agent, chat, message)

        @wraps(func)
        def dialog_wrapper(self):
            if not issubclass(self.agent, cls):
                raise NotPassed
            if self.message.chat.id != chat:
                raise NotPassed
            return func(self)

        return dialog_wrapper if is_dialog else func_wrapper

    return decorator


def only_telegram_callback(is_dialog: bool=False):
    def decorator(func: Callable):
        @wraps(func)
        def func_wrapper(agent: Agent, chat: Chat, message: Message):
            if isinstance(agent, TelegramAgent) and isinstance(message, TelegramCallback):
                return func(agent, chat, message)
            raise NotPassed

        @wraps(func)
        def dialog_wrapper(self):
            if isinstance(self.agent, TelegramAgent) and isinstance(self.message, TelegramCallback):
                return func(self, self.message.text)
            raise NotPassed

        return dialog_wrapper if is_dialog else func_wrapper

    return decorator
