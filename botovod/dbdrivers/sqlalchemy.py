from botovod import Attachment, Chat, Location, Message as BotoMessage, dbdrivers
from datetime import datetime
import json
from json import JSONDecodeError
import logging
from sqlalchemy import Column, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.types import Boolean, Date, Integer, DateTime, String, Text


def commit(func):
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if not result is None:
            DBDriver.session.add_all(result)
        DBDriver.session.commit()
        return result
    return wrapper


Base = declarative_base()


class Common:
    id = Column(Integer, autoincrement=True, index=True, nullable=False, primary_key=True,
                unique=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)


class Bot(Common, Base):
    __tablename__ = "bots"

    name = Column(String(64), nullable=False, unique=True)
    agent = Column(String(64), nullable=False)
    settings = Column(Text, nullable=False, default="{}")
    followers = relationship("Follower", back_populates="bot", uselist=True)


class Follower(dbdrivers.Follower, Common, Base):
    __tablename__ = "followers"

    chat = Column(String(64), nullable=False)
    bot_id = Column(Integer, ForeignKey(f"{Bot.__tablename__}.id"), nullable=False)
    bot = relationship("Bot", back_populates="followers", uselist=False)
    dialog = Column(String(64))
    next_step = Column(String(64))
    data = Column(Text, nullable=False, default="{}")
    messages = relationship("Message", back_populates="follower", uselist=True)

    def get_chat(self):
        return Chat(self.bot.agent, self.chat)

    def get_dialog_name(self):
        return self.dialog

    @commit
    def set_dialog_name(self, name):
        self.dialog = name
        return [self]

    def get_next_step(self):
        return self.next_step

    @commit
    def set_next_step(self, next_step):
        self.next_step = next_step
        return [self]

    def get_history(self, after_date=None, before_date=None, input=None, text=None):
        messages = self.messages
        if not after_date is None:
            messages = messages.filter(Message.date >= after_date)
        if not before_date is None:
            messages = messages.filter(Message.date <= before_date)
        if not input is None:
            messages = messages.filter(Message.input == input)
        if not text is None:
            messages = messages.filter(Message.text.like(text))
        return [message.to_object() for message in messages.all()]

    @commit
    def add_history(self, message, input=True):
        return [Message(
            follower_id = self.id,
            input = input,
            text = message.text,
            images = json.loads([attachment_render(image) for image in message.images]),
            audios = json.loads([attachment_render(audio) for audio in message.audios]),
            videos = json.loads([attachment_render(video) for video in message.videos]),
            documents = json.loads([attachment_render(document) for document in message.documents]),
            locations = json.loads([location_render(location) for location in message.locations]),
            raw = json.loads(message.raw),
            date = message.date,
        )]

    @commit
    def clear_history(self, after_date=None, before_date=None, input=None, text=None):
        messages = self.messages
        if not after_date is None:
            messages = messages.filter(Message.date >= after_date)
        if not before_date is None:
            messages = messages.filter(Message.date <= before_date)
        if not input is None:
            messages = messages.filter(Message.input == input)
        if not text is None:
            messages = messages.filter(Message.text.like(text))
        messages.delete()
        return messages

    def get_value(self, name):
        try:
            return json.loads(self.data)[name]
        except KeyError:
            logging.warning("Value '%s' doesn't exist for follower %s %s", name, self.bot.agent,
                            self.chat)
        except JSONDecodeError:
            logging.error("Cannot get value '%s' for follower %s %s - incorrect json", name,
                          self.bot.agent, self.chat)

    @commit
    def set_value(self, name, value):
        try:
            data = json.loads(self.data)
        except JSONDecodeError:
            logging.error("Incorrect json structure for follower %s %s", self.bot.agent, self.chat)
            data = dict()
        data[name] = value
        self.data = json.dumps(data)
        return [self]

    @commit
    def delete_value(self, name):
        data = json.loads(self.obj.data)
        try:
            del data[name]
        except KeyError:
            logging.warning("Cannot delete value '%s' for follower %s %s - doesn't exist", name,
                            self.bot.agent, self.chat)
        self.data = json.dumps(data)
        return [self]


class Message(Common, Base):
    __tablename__ = "messages"

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
    def connect(cls, type, database, host=None, username=None, password=None, debug=False):
        string = f"{type}://"
        if not username is None and not password is None:
            string = string + f"{username}:{password}@"
        if not host is None:
            string = string + f"{host}/"
        string = string + database
        cls.engine = create_engine(string, echo=debug)
        cls.metadata = Base.metadata
        cls.metadata.create_all(cls.engine)
        Session = sessionmaker()
        Session.configure(bind=cls.engine)
        cls.session = Session()

    @classmethod
    def get_follower(cls, agent, chat):
        follower = cls.session.query(Follower).filter(Follower.bot.name == agent.name)
        return follower.filter(Follower.chat == chat.id).first()

    @commit
    @classmethod
    def add_follower(cls, agent, chat):
        bot = cls.session.query(Bot).filter(name=agent.name).first()
        return Follower(
            chat=chat.id,
            bot_id=bot.id,
        )

    @commit
    @classmethod
    def delete_follower(cls, agent, chat):
        follower = cls.session.query(Follower).filter(Follower.agent == agent.__class__.__name__)
        follower = follower.filter(Follower.chat == chat.id)
        follower.delete()
        return follower


def attachment_render(attachment):
    return {
        "url": attachment.url,
        "file": attachment.file,
        "raw": attachment.raw,
    }


def attachment_parser(data):
    attachment = Attachment
    attachment.url = data["url"]
    attachment.file = data["file"]
    attachment.raw = data["raw"]
    return attachment


def location_render(location):
    return {
        "longitude": location.longitude,
        "latitude": location.latitude,
        "raw": location.raw,
    }


def location_parser(data):
    location = Location(
        longitude = data["longitude"],
        latitude = data["latitude"],
    )
    location.raw = data["raw"]
    return location
