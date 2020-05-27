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
from typing import Any, Callable, Dict, Iterable, Optional, Union


Base = declarative_base()
logger = logging.getLogger(__name__)


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

    def get_dialog(self) -> Optional[str]:

        return self.dialog

    @add(one=True)
    def set_dialog(self, name: Optional[str]=None):

        self.dialog = name
        self.set_next_step(None if name is None else "start")
        return self

    def get_next_step(self) -> Optional[str]:

        return self.next_step

    @add(one=True)
    def set_next_step(self, next_step: Optional[str]=None):

        self.next_step = next_step
        return self

    def get_history(self, after: Optional[datetime]=None, before: Optional[datetime]=None,
                    input: Optional[bool]=None, text: Optional[str]=None) -> Iterable[BotoMessage]:

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

    @add(one=True)
    def add_history(self, datetime: datetime, text: Optional[str]=None,
                    images: Iterable[Attachment]=(), audios: Iterable[Attachment]=(),
                    videos: Iterable[Attachment]=(), documents: Iterable[Attachment]=(),
                    locations: Iterable[Location]=(), input: bool=True, **raw):

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
    def clear_history(self, after: Optional[datetime]=None, before: Optional[datetime]=None,
                      input: Optional[bool]=None, text: Optional[str]=None):

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

    def get_values(self) -> dict:

        try:
            return json.loads(self.data)
        except JSONDecodeError:
            logger.error("Cannot get values for follower %s %s - incorrect json", self.bot,
                         self.chat)

    def get_value(self, name: str, default=None):

        try:
            return json.loads(self.data)[name]
        except KeyError:
            return default
        except JSONDecodeError:
            logger.error("Cannot get value '%s' for follower %s %s - incorrect json", name,
                         self.bot, self.chat)

    @add(one=True)
    def set_value(self, name: str, value):

        try:
            data = json.loads(self.data)
        except JSONDecodeError:
            logger.error("Incorrect json structure for follower %s %s", self.bot, self.chat)
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
            pass
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
    def connect(self, engine: str, database: str, host: Optional[Union[str, int]]=None,
                username: Optional[str]=None, password: Optional[str]=None, debug: bool=False):

        dsn = f"{engine}://"
        if username is not None and password is not None:
            dsn += f"{username}:{password}@"
        if host is not None:
            dsn += f"{host}/"
        dsn += database
        self.engine = create_engine(dsn, echo=debug)
        self.metadata = Base.metadata
        self.metadata.create_all(self.engine)
        Session = sessionmaker()
        Session.configure(bind=self.engine)
        self.session = Session()

    def get_follower(self, agent: Agent, chat: Chat) -> Follower:

        follower = self.session.query(Follower).filter(Follower.bot == agent.name)
        return follower.filter(Follower.chat == chat.id).first()

    @add(one=True)
    def add_follower(self, agent: Agent, chat: Chat) -> Follower:

        follower = Follower(chat=chat.id, bot=agent.name)
        return follower

    @delete(one=True)
    def delete_follower(self, agent: Agent, chat: Chat):

        follower = self.session.query(Follower).filter(Follower.bot == agent.name)
        follower = follower.filter(Follower.chat == chat.id)
        return follower
