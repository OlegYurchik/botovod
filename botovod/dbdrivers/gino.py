from botovod import dbdrivers
from botovod.agents import Agent, Attachment, Chat, Location, Message as BotoMessage
from datetime import datetime
import gino
import json
from json import JSONDecodeError
import logging
from typing import Dict, Iterable


db = gino.Gino()


class Common:
    id = db.Column(db.Integer, autoincrement=True, index=True, nullable=False, primary_key=True,
                   unique=True)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)


class Follower(dbdrivers.Follower, Common, db.Model):
    __tablename__ = "botovod_followers"

    chat = db.Column(db.Unicode(length=64), nullable=False)
    bot = db.Column(db.Unicode(length=64), nullable=False)
    dialog = db.Column(db.Unicode(length=64), nullable=True)
    next_step = db.Column(db.Unicode(length=64), nullable=True)
    data = db.Column(db.Text, nullable=False, default="{}")

    async def a_get_chat(self) -> Chat:
        return Chat(self.bot, self.chat)

    async def a_get_dialog(self) -> (str, None):
        return self.dialog

    async def a_set_dialog(self, name: (str, None)=None):
        await self.update(dialog=name).apply()
        await self.a_set_next_step(None if name is None else "start")

    async def a_get_next_step(self) -> (str, None):
        return self.next_step
    
    async def a_set_next_step(self, next_step: (str, None)=None):
        await self.update(next_step=next_step).apply()

    async def a_get_history(self, after_date: (datetime, None)=None,
                            before_date: (datetime, None)=None, input: (bool, None)=None,
                            text: (str, None)=None) -> Iterable[BotoMessage]:
        condition = Message.follower_id == self.id
        if after_date is not None:
            condition = condition and Message.date >= after_date
        if before_date is not None:
            condition = condition and Message.date <= before_date
        if input is not None:
            condition = condition and Message.input == input
        if text is not None:
            condition = condition and Message.text.like(text)
        return [message.to_object() for message in await Message.query.where(condition).gino.all()]

    async def a_add_history(self, datetime: datetime, text: (str, None)=None,
                            images: Iterable[Attachment]=[], audios: Iterable[Attachment]=[],
                            videos: Iterable[Attachment]=[], documents: Iterable[Attachment]=[],
                            locations: Iterable[Location]=[], raw: dict={}, input: bool=True):
        await Message.create(
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

    async def a_clear_history(self, after: (datetime, None)=None, before: (datetime, None)=None,
                              input: (datetime, None)=None, text: (str, None)=None):
        condition = Message.follower_id == self.id
        if not after is None:
            condition = condition and Message.datetime >= after
        if not before is None:
            condition = condition and Message.datetime <= before
        if not input is None:
            condition = condition and Message.input == input
        if not text is None:
            condition = condition and Message.text.like(text)
        await Message.delete.where(condition).gino.status()

    async def a_get_values(self) -> Dict[str, str]:
        try:
            return json.loads(self.data)
        except JSONDecodeError:
            logging.error("Cannot get values for follower %s %s - incorrect json", self.bot,
                          self.chat)

    async def a_get_value(self, name: str) -> str:
        try:
            return json.loads(self.data)[name]
        except KeyError:
            logging.warning("Value '%s' doesn't exist for follower %s %s", name, self.bot,
                            self.chat)
        except JSONDecodeError:
            logging.error("Cannot get value '%s' for follower %s %s - incorrect json", name,
                          self.bot, self.chat)

    async def a_set_value(self, name: str, value: str):
        try:
            data = json.loads(self.data)
        except JSONDecodeError:
            logging.error("Incorrect json structure for follower %s %s", self.bot, self.chat)
            data = dict()
        data[name] = value
        await self.update(data=json.dumps(data)).apply()

    async def a_delete_value(self, name: str):
        data = json.loads(self.data)
        try:
            del data[name]
        except KeyError:
            logging.warning("Cannot delete value '%s' for follower %s %s - doesn't exist", name,
                            self.bot, self.chat)
        await self.update(data=json.dumps(data)).apply()

    async def a_clear_values(self):
        await self.update(data="{}").apply()


class Message(Common, db.Model):
    __tablename__ = "botovod_messages"

    follower_id = db.Column(db.Integer, db.ForeignKey(f"{Follower.__tablename__}.id"),
                            nullable=False)    
    input = db.Column(db.Boolean, nullable=False)
    text = db.Column(db.Text)
    images = db.Column(db.Text, nullable=False, default="[]")
    audios = db.Column(db.Text, nullable=False, default="[]")
    videos = db.Column(db.Text, nullable=False, default="[]")
    documents = db.Column(db.Text, nullable=False, default="[]")
    locations = db.Column(db.Text, nullable=False, default="[]")
    raw = db.Column(db.Text)
    datetime = db.Column(db.DateTime, nullable=False)

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
        return message


class DBDriver(dbdrivers.DBDriver):
    db = db

    @classmethod
    async def a_connect(cls, engine: str, database: str, host: (str, int, None)=None,
                        username: (str, None)=None, password: (str, None)=None):
        try:
            await cls.db.pop_bind().close()
        except gino.exceptions.UninitializedError:
            pass
        dsn = f"{engine}://"
        if username is not None and password is not None:
            dsn += f"{username}:{password}@"
        if host is not None:
            dsn += f"{host}/"
        dsn += database
        await cls.db.set_bind(dsn)
        await cls.db.gino.create_all()

    @classmethod
    async def a_get_follower(cls, agent: Agent, chat: Chat) -> (Follower, None):
        return await Follower.query.where(Follower.bot == agent.__class__.__name__).where(
            Follower.chat == chat.id
        ).gino.first()

    @classmethod
    async def a_add_follower(cls, agent: Agent, chat: Chat) -> Follower:
        return await Follower.create(bot=agent.__class__.__name__, chat=chat.id)

    @classmethod
    async def a_delete_follower(cls, agent: Agent, chat: Chat):
        await Follower.delete.where(Follower.bot == agent.__class__.__name__).where(
            Follower.chat == chat.id
        ).gino.status()
