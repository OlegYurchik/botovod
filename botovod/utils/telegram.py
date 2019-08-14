from botovod.agents import Agent, Chat, Message
from botovod.agents.telegram import TelegramAgent, TelegramCallback
from botovod.utils.exceptions import NotPassed
from typing import Callable


def only_telegram_callbacks(is_dialog: bool=False):
    def decorator(func: Callable):
        def func_wrapper(agent: Agent, chat: Chat, message: Message):
            if isinstance(agent, TelegramAgent) and isinstance(message, TelegramCallback):
                return func(agent, chat, message)
            raise NotPassed

        def dialog_wrapper(self):
            if isinstance(self.agent, TelegramAgent) and isinstance(self.message, TelegramCallback):
                return func(self.agent, self.chat, self.message)
            raise NotPassed

        return dialog_wrapper if is_dialog else func_wrapper

    return decorator
