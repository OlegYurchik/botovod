from botovod.agents import Agent, Chat
from botovod.utils.exceptions import NotPassed
import re


def to_text(func):
    def wrapper(agent, chat, message):
        if message.text is None:
            raise NotPassed
        return func(agent, chat, message.text)
    return wrapper


def to_attachments(func):
    def wrapper(agent, chat, message):
        attachments = []
        attachments.extend(message.images)
        attachments.extend(message.audios)
        attachments.extend(message.videos)
        attachments.extend(message.documents)
        if not attachments:
            raise NotPassed
        return func(agent, chat, attachments)
    return wrapper


def to_images(func):
    def wrapper(agent, chat, message):
        if not message.images:
            raise NotPassed
        return func(agent, chat, message.images)
    return wrapper


def to_audios(func):
    def wrapper(agent, chat, message):
        if not message.audios:
            raise NotPassed
        return func(agent, chat, message.audios)
    return wrapper


def to_videos(func):
    def wrapper(agent, chat, message):
        if not message.videos:
            raise NotPassed
        return func(agent, chat, message.videos)
    return wrapper


def to_documents(func):
    def wrapper(agent, chat, message):
        if not message.documents:
            raise NotPassed
        return func(agent, chat, message.documents)
    return wrapper


def to_locations(func):
    def wrapper(agent, chat, message):
        if not message.locations:
            raise NotPassed
        return func(agent, chat, message.locations)
    return wrapper


def only_regexp(expression):
    def decorator(func):
        def wrapper(agent, chat, message):
            if message.text is None:
                raise NotPassed
            match = re.match(expression, message.text)
            if not match:
                raise NotPassed
            return func(agent, chat, *match.groups())
        return wrapper
    return decorator


def only_agent(name):
    def decorator(func):
        def wrapper(agent, chat, message):
            if agent.name != name:
                raise NotPassed
            return func(agent, chat, message)
        return wrapper
    return decorator


def only_chat(chat, cls: Agent=Agent):
    def decorator(func):
        def wrapper(agent, chat, message):
            if not issubclass(agent, cls):
                raise NotPassed
            if message.chat.id != chat:
                raise NotPassed
            return func(agent, chat, message)
        return wrapper
    return decorator
