from botovod import dbdrivers
from botovod.agents import Agent, Chat
from datetime import datetime
import gino
import json
import logging
from typing import Dict, Optional, Union


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

    async def a_set_dialog(self, name: Optional[str] = None):
        await self.update(dialog=name).apply()

    async def a_get_next_step(self) -> Optional[str]:
        return self.next_step

    async def a_set_next_step(self, next_step: Optional[str] = None):
        await self.update(next_step=next_step).apply()

    async def a_get_values(self) -> Dict[str, str]:
        return json.loads(self.data)

    async def a_get_value(self, name: str, default: Optional[str] = None) -> Optional[str]:
        return json.loads(self.data).get(name, default)

    async def a_set_value(self, name: str, value: str):
        data = json.loads(self.data)
        data[name] = value
        await self.update(data=data).apply()

    async def a_delete_value(self, name: str):
        data = json.loads(self.data)
        if name in data:
            del data[name]
        await self.update(data=data).apply()

    async def a_clear_values(self):
        await self.update(data="{}").apply()


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

    async def a_delete(self, follower: Follower):
        await follower.delete()
