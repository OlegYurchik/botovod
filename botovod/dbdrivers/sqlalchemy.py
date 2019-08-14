from __future__ import annotations
from botovod import dbdrivers
from botovod.agents import Agent, Attachment, Chat, Location, Message as BotoMessage
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
    dialog = Column(String(64), nullable=True)
    next_step = Column(String(64), nullable=True)
    data = Column(Text, nullable=False, default="{}")
    messages = relationship("Message", back_populates="follower", uselist=True)

    def get_chat(self) -> Chat:
        return Chat(self.bot, self.chat)

    def get_dialog(self) -> (str, None):
        return self.dialog

    @add()
    def set_dialog(self, name: (str, None)=None):
        self.dialog = name
        self.set_next_step(None if name is None else "start")
        return self

    def get_next_step(self) -> (str, None):
        return self.next_step

    @add()
    def set_next_step(self, next_step: (str, None)=None):
        self.next_step = next_step
        return self

    def get_history(self, after: (datetime, None)=None, before: (datetime, None)=None,
                    input: (bool, None)=None, text: (str, None)=None) -> Iterable[BotoMessage]:
        messages = self.messages
        if after is not None:
            messages = messages.filter(Message.datetime >= after)
        if before is not None:
            messages = messages.filter(Message.datetime <= before)
        if input is not None:
            messages = messages.filter(Message.input == input)
        if text is not None:
            messages = messages.filter(Message.text.like(text))
        return [message.to_object() for message in messages.all()]

    @add()
    def add_history(self, datetime: datetime, text: (str, None)=None,
                    images: Iterable[Attachment]=[], audios: Iterable[Attachment]=[],
                    videos: Iterable[Attachment]=[], documents: Iterable[Attachment]=[],
                    locations: Iterable[Location]=[], input: bool=True, **raw):
        return Message(
            follower_id=self.id,
            input=input,
            text=text,
            images=json.loads([image.__dict__ for image in images]),
            audios=json.loads([audio.__dict__ for audio in audios]),
            videos=json.loads([video.__dict__ for video in videos]),
            documents=json.loads([document.__dict__ for document in documents]),
            locations=json.loads([location.__dict__ for location in locations]),
            raw=json.loads(raw),
            datetime=datetime,
        )

    @delete(one=False)
    def clear_history(self, after: (datetime, None)=None, before: (datetime, None)=None,
                      input: (bool, None)=None, text: (str, None)=None):
        messages = self.messages
        if not after is None:
            messages = messages.filter(Message.datetime >= after)
        if not before is None:
            messages = messages.filter(Message.datetime <= before)
        if not input is None:
            messages = messages.filter(Message.input == input)
        if not text is None:
            messages = messages.filter(Message.text.like(text))
        return messages

    def get_values(self) -> Dict[str, str]:
        try:
            return json.loads(self.data)
        except JSONDecodeError:
            logging.error("Cannot get values for follower %s %s - incorrect json", self.bot,
                          self.chat)

    def get_value(self, name: str) -> str:
        try:
            return json.loads(self.data)[name]
        except KeyError:
            logging.warning("Value '%s' doesn't exist for follower %s %s", name, self.bot,
                            self.chat)
        except JSONDecodeError:
            logging.error("Cannot get value '%s' for follower %s %s - incorrect json", name,
                          self.bot, self.chat)

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

    @update()
    def clear_values(self):
        self.data = "{}"


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
    datetime = Column(Date, nullable=False)

    @staticmethod
    def parser(cls, data: dict):
        obj = cls()
        for key, value in data.items():
            obj.__setattr__(key, value)
        return obj

    def to_object(self):
        message = BotoMessage()
        message.text = self.text
        message.images = [self.parser(Attachment, image) for image in json.loads(self.images)]
        message.audios = [self.parser(Attachment, audio) for audio in json.loads(self.audios)]
        message.videos = [self.parser(Attachment, video) for video in json.loads(self.videos)]
        message.documents = [
            self.parser(Attachment, document) for document in json.loads(self.documents)
        ]
        message.locations = [
            self.parser(Location, location) for location in json.loads(self.locations)
        ]
        message.raw = json.loads(self.raw)
        return message


class DBDriver(dbdrivers.DBDriver):
    @classmethod
    def connect(cls, engine: str, database: str, host: (str, int, None)=None,
                username: (str, None)=None, password: (str, None)=None, debug: bool=False):
        dsn = f"{engine}://"
        if username is not None and password is not None:
            dsn += f"{username}:{password}@"
        if host is not None:
            dsn += f"{host}/"
        dsn += database
        cls.engine = create_engine(dsn, echo=debug)
        cls.metadata = Base.metadata
        cls.metadata.create_all(cls.engine)
        Session = sessionmaker()
        Session.configure(bind=cls.engine)
        cls.session = Session()

    @classmethod
    def get_follower(cls, agent: Agent, chat: Chat) -> Follower:
        follower = cls.session.query(Follower).filter(Follower.bot == agent.name)
        return follower.filter(Follower.chat == chat.id).first()

    @classmethod
    @add()
    def add_follower(cls, agent: Agent, chat: Chat) -> Follower:
        follower = Follower(chat=chat.id, bot=agent.name)
        return follower

    @classmethod
    @delete()
    def delete_follower(cls, agent: Agent, chat: Chat):
        follower = cls.session.query(Follower).filter(Follower.bot == agent.name)
        follower = follower.filter(Follower.chat == chat.id)
        return follower
