from __future__ import annotations
from botovod import dbdrivers
from botovod.agents import (Agent, Attachment, Audio, Chat, Document, Image, Location,
                            Message as BotoMessage, Video)
from datetime import datetime
import json
from json import JSONDecodeError
import logging
from sqlalchemy import Column, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.types import Boolean, Date, Integer, DateTime, String, Text
from typing import Any, Callable, Dict, Iterable


Base = declarative_base()


def attachment_render(attachment: Attachment) -> dict:
    return {
        "url": attachment.url,
        "file": attachment.file,
        "raw": attachment.raw,
    }


def attachment_parser(data: dict) -> Attachment:
    attachment = Attachment
    attachment.url = data["url"]
    attachment.file = data["file"]
    attachment.raw = data["raw"]
    return attachment


def location_render(location: Location) -> dict:
    return {
        "longitude": location.longitude,
        "latitude": location.latitude,
        "raw": location.raw,
    }


def location_parser(data: dict) -> Location:
    location = Location(
        longitude = data["longitude"],
        latitude = data["latitude"],
    )
    location.raw = data["raw"]
    return location


def add(one: bool=True):
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if result is not None:
                if one:
                    DBDriver.session.add(result)
                else:
                    DBDriver.session.add_all(result)
            DBDriver.session.commit()
            return result
        return wrapper
    return decorator


def delete(one: bool=True):
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if result is not None:
                if one:
                    DBDriver.session.delete(result)
                else:
                    DBDriver.session.delete_all(result)
            DBDriver.session.commit()
            return result
        return wrapper
    return decorator


def update():
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            DBDriver.session.commit()
            return result
        return wrapper
    return decorator


class Common:
    id = Column(Integer, autoincrement=True, index=True, nullable=False, primary_key=True,
                unique=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)


class Follower(dbdrivers.Follower, Common, Base):
    __tablename__ = "botovod_followers"

    chat = Column(String(64), nullable=False)
    bot = Column(String(64), nullable=False)
    dialog = Column(String(64))
    next_step = Column(String(64))
    data = Column(Text, nullable=False, default="{}")
    messages = relationship("Message", back_populates="follower", uselist=True)

    def get_chat(self) -> Chat:
        return Chat(self.bot, self.chat)

    async def a_get_chat(self) -> Chat:
        pass

    def get_dialog(self) -> str:
        return self.dialog

    async def a_get_dialog(self) -> str:
        pass

    @add()
    def set_dialog(self, name: (str, None)=None):
        self.dialog = name
        self.set_next_step("start")
        return self

    async def a_set_dialog(self, name: (str, None)=None):
        pass

    def get_next_step(self) -> str:
        return self.next_step

    async def a_get_next_step(self) -> str:
        pass

    @add()
    def set_next_step(self, next_step: (str, None)=None):
        self.next_step = next_step
        return self

    async def a_set_next_step(self, next_step: (str, None)=None):
        pass

    def get_history(self, after_date: (datetime, None)=None, before_date: (datetime, None)=None,
                    input: (bool, None)=None, text: (str, None)=None) -> Iterable[BotoMessage]:
        messages = self.messages
        if after_date is not None:
            messages = messages.filter(Message.date >= after_date)
        if before_date is not None:
            messages = messages.filter(Message.date <= before_date)
        if input is not None:
            messages = messages.filter(Message.input == input)
        if text is not None:
            messages = messages.filter(Message.text.like(text))
        return [message.to_object() for message in messages.all()]

    async def a_get_history(self, after_date: (datetime, None)=None,
                            before_date: (datetime, None)=None, input: (bool, None)=None,
                            text: (str, None)=None) -> Iterable[BotoMessage]:
        pass

    @add()
    def add_history(self, date: datetime, text: (str, None)=None, images: Iterable[Image]=[],
                    audios: Iterable[Audio]=[], videos: Iterable[Video]=[],
                    documents: Iterable[Document]=[], locations: Iterable[Location]=[],
                    raw: Any=None, input: bool=True):
        return Message(
            follower_id = self.id,
            input = input,
            text = text,
            images = json.loads([attachment_render(image) for image in images]),
            audios = json.loads([attachment_render(audio) for audio in audios]),
            videos = json.loads([attachment_render(video) for video in videos]),
            documents = json.loads([attachment_render(document) for document in documents]),
            locations = json.loads([location_render(location) for location in locations]),
            raw = json.loads(raw),
            date = date,
        )

    async def a_add_history(self, date: datetime, text: (str, None)=None,
                            images: Iterable[Image]=[], audios: Iterable[Audio]=[],
                            videos: Iterable[Video]=[], documents: Iterable[Document]=[],
                            locations: Iterable[Location]=[], raw: Any=None, input: bool=True):
        pass

    @delete(one=False)
    def clear_history(self, after_date: (datetime, None)=None, before_date: (datetime, None)=None,
                      input: (datetime, None)=None, text: (str, None)=None):
        messages = self.messages
        if not after_date is None:
            messages = messages.filter(Message.date >= after_date)
        if not before_date is None:
            messages = messages.filter(Message.date <= before_date)
        if not input is None:
            messages = messages.filter(Message.input == input)
        if not text is None:
            messages = messages.filter(Message.text.like(text))
        return messages

    async def a_clear_history(self, after_date: (datetime, None)=None,
                              before_date: (datetime, None)=None, input: (datetime, None)=None,
                              text: (str, None)=None):
        pass

    def get_values(self) -> Dict[str, str]:
        try:
            return json.loads(self.data)
        except JSONDecodeError:
            logging.error("Cannot get values for follower %s %s - incorrect json", self.bot,
                          self.chat)

    async def a_get_values(self) -> Dict[str, str]:
        pass

    def get_value(self, name: str) -> str:
        try:
            return json.loads(self.data)[name]
        except KeyError:
            logging.warning("Value '%s' doesn't exist for follower %s %s", name, self.bot,
                            self.chat)
        except JSONDecodeError:
            logging.error("Cannot get value '%s' for follower %s %s - incorrect json", name,
                          self.bot, self.chat)

    async def a_get_value(self, name: str):
        pass

    @add()
    def set_value(self, name: str, value: str):
        try:
            data = json.loads(self.data)
        except JSONDecodeError:
            logging.error("Incorrect json structure for follower %s %s", self.bot, self.chat)
            data = dict()
        data[name] = value
        self.data = json.dumps(data)
        return self

    async def a_set_value(self, name: str, value: str):
        pass

    @update()
    def delete_value(self, name: str):
        data = json.loads(self.data)
        try:
            del data[name]
        except KeyError:
            logging.warning("Cannot delete value '%s' for follower %s %s - doesn't exist", name,
                            self.bot, self.chat)
        self.data = json.dumps(data)
        return self

    async def a_delete_value(self, name: str):
        pass

    @update()
    def clear_values(self):
        self.data = "{}"

    async def a_clear_values(self):
        pass


class Message(Common, Base):
    __tablename__ = "botovod_messages"

    follower_id = Column(Integer, ForeignKey(f"{Follower.__tablename__}.id"), nullable=False)    
    follower = relationship("Follower", back_populates="messages", uselist=False)
    input = Column(Boolean, nullable=False)
    text = Column(Text)
    images = Column(Text, nullable=False, default="[]")
    audios = Column(Text, nullable=False, default="[]")
    videos = Column(Text, nullable=False, default="[]")
    documents = Column(Text, nullable=False, default="[]")
    locations = Column(Text, nullable=False, default="[]")
    raw = Column(Text)
    date = Column(Date, nullable=False)

    def to_object(self):
        message = BotoMessage()
        message.text = self.text
        message.images = [attachment_parser(image) for image in json.loads(self.images)]
        message.audios = [attachment_parser(audio) for audio in json.loads(self.audios)]
        message.videos = [attachment_parser(video) for video in json.loads(self.videos)]
        message.documents = [attachment_parser(document) for document in json.loads(self.documents)]
        message.locations = [location_parser(location) for location in json.loads(self.locations)]
        message.raw = json.loads(self.raw)
        return message


class DBDriver(dbdrivers.DBDriver):
    @classmethod
    def connect(cls, type: str, database: str, host: (str, int, None)=None,
                username: (str, None)=None, password: (str, None)=None, debug: bool=False):
        string = f"{type}://"
        if username is not None and password is not None:
            string = string + f"{username}:{password}@"
        if host is not None:
            string = string + f"{host}/"
        string = string + database
        cls.engine = create_engine(string, echo=debug)
        cls.metadata = Base.metadata
        cls.metadata.create_all(cls.engine)
        Session = sessionmaker()
        Session.configure(bind=cls.engine)
        cls.session = Session()

    @classmethod
    async def a_connect(cls, type: str, database: str, host: (str, int, None)=None,
                        username: (str, None)=None, password: (str, None)=None, debug: bool=False):
        pass

    @classmethod
    def get_follower(cls, agent: Agent, chat: Chat) -> Follower:
        follower = cls.session.query(Follower).filter(Follower.bot == agent.name)
        return follower.filter(Follower.chat == chat.id).first()

    @classmethod
    async def a_get_follower(cls, agent: Agent, chat: Chat) -> Follower:
        pass

    @classmethod
    @add()
    def add_follower(cls, agent: Agent, chat: Chat) -> Follower:
        follower = Follower(chat=chat.id, bot=agent.name)
        return follower

    @classmethod
    async def a_add_follower(cls, agent: Agent, chat: Chat) -> Follower:
        pass

    @classmethod
    @delete()
    def delete_follower(cls, agent: Agent, chat: Chat):
        follower = cls.session.query(Follower).filter(Follower.bot == agent.name)
        follower = follower.filter(Follower.chat == chat.id)
        return follower

    @classmethod
    async def a_delete_follower(cls, agent: Agent, chat: Chat):
        pass
