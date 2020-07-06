from botovod import dbdrivers
from botovod.agents import Agent, Attachment, Chat, Location, Message as BotoMessage
from datetime import datetime
import gino
import json
from json import JSONDecodeError
import logging
from typing import Dict, Iterable, Optional, Union


db = gino.Gino()
logger = logging.getLogger(__name__)


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

    async def a_get_dialog(self) -> Optional[str]:

        return self.dialog

    async def a_set_dialog(self, name: Optional[str]=None):

        await self.update(dialog=name, next_step=None if name is None else "start").apply()

    async def a_get_next_step(self) -> Optional[str]:

        return self.next_step
    
    async def a_set_next_step(self, next_step: Optional[str]=None):

        await self.update(next_step=next_step).apply()

    async def a_get_history(self, after_date: Optional[datetime]=None,
                            before_date: Optional[datetime]=None, input: Optional[bool]=None,
                            text: Optional[str]=None) -> Iterable[BotoMessage]:

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

    async def a_add_history(self, datetime: datetime, text: Optional[str]=None,
                            images: Iterable[Attachment]=(), audios: Iterable[Attachment]=(),
                            videos: Iterable[Attachment]=(), documents: Iterable[Attachment]=(),
                            locations: Iterable[Location]=(), raw: Optional[dict]=None,
                            input: bool=True):

        if not raw:
            raw = {}
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

    async def a_clear_history(self, after: Optional[datetime]=None, before: Optional[datetime]=None,
                              input: Optional[datetime]=None, text: Optional[str]=None):

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

    async def a_get_values(self) -> dict:

        try:
            return json.loads(self.data)
        except JSONDecodeError:
            logger.error("Cannot get values for follower %s %s - incorrect json", self.bot,
                         self.chat)

    async def a_get_value(self, name: str, default=None):

        try:
            return json.loads(self.data)[name]
        except KeyError:
            return default
        except JSONDecodeError:
            logger.error("Cannot get value '%s' for follower %s %s - incorrect json", name,
                         self.bot, self.chat)

    async def a_set_value(self, name: str, value: str):

        try:
            data = json.loads(self.data)
        except JSONDecodeError:
            logger.error("Incorrect json structure for follower %s %s", self.bot, self.chat)
            data = dict()
        data[name] = value
        await self.update(data=json.dumps(data)).apply()

    async def a_delete_value(self, name: str):

        data = json.loads(self.data)
        try:
            del data[name]
        except KeyError:
            return
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

    async def a_connect(self, engine: str, database: str, host: Optional[Union[str, int]]=None,
                        username: Optional[str]=None, password: Optional[str]=None):
        await self.a_close()
        dsn = f"{engine}://"
        if username is not None and password is not None:
            dsn += f"{username}:{password}@"
        if host is not None:
            dsn += f"{host}/"
        dsn += database
        await self.db.set_bind(dsn)

    async def a_close(self):
        try:
            await self.db.pop_bind().close()
        except gino.exceptions.UninitializedError:
            pass

    async def a_get_follower(self, agent: Agent, chat: Chat) -> Optional[Follower]:

        return await Follower.query.where(Follower.bot == agent.__class__.__name__).where(
            Follower.chat == chat.id
        ).gino.first()

    async def a_add_follower(self, agent: Agent, chat: Chat) -> Follower:

        return await Follower.create(bot=agent.__class__.__name__, chat=chat.id)

    async def a_delete_follower(self, agent: Agent, chat: Chat):

        await Follower.delete.where(Follower.bot == agent.__class__.__name__).where(
            Follower.chat == chat.id
        ).gino.status()
