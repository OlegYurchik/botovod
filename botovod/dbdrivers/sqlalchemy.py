from __future__ import annotations
from botovod import dbdrivers
from botovod.agents import Agent, Chat
from datetime import datetime
import json
import logging
from sqlalchemy import Column, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.types import Boolean, Date, Integer, DateTime, String, Text
from typing import Dict, Optional, Union


Base = declarative_base()
logger = logging.getLogger(__name__)


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

    def set_dialog(self, name: Optional[str] = None):
        self.dialog = name
        self.set_next_step(None if name is None else "start")

    def get_next_step(self) -> Optional[str]:
        return self.next_step

    def set_next_step(self, next_step: Optional[str] = None):
        self.next_step = next_step
        self._dbdriver.session.add(self)
        self._dbdriver.session.commit()

    def get_values(self) -> Dict[str, str]:
        return json.loads(self.data)

    def get_value(self, name: str, default: Optional[str] = None) -> Optional[str]:
        return json.loads(self.data).get(name, default)

    def set_value(self, name: str, value: str):
        data = json.loads(self.data)
        data[name] = value
        self.data = json.dumps(data)
        self._dbdriver.session.add(self)
        self._dbdriver.commit()

    def delete_value(self, name: str):
        data = json.loads(self.data)
        if name in data:
            del data[name]
        self.data = json.dumps(data)
        self._dbdriver.session.commit()

    def clear_values(self):
        self.data = "{}"
        self._dbdriver.session.commit()


class DBDriver(dbdrivers.DBDriver):
    def connect(self, engine: str, database: str, host: Optional[Union[str, int]] = None,
                username: Optional[str] = None, password: Optional[str] = None,
                debug: bool = False):
        dsn = f"{engine}://"
        if username is not None and password is not None:
            dsn += f"{username}:{password}@"
        if host is not None:
            dsn += f"{host}/"
        dsn += database
        self.engine = create_engine(dsn, echo=debug)
        self.metadata = Base.metadata
        Session = sessionmaker()
        Session.configure(bind=self.engine)
        self.session = Session()

    def close(self):
        self.session.close()

    def get_follower(self, agent: Agent, chat: Chat) -> Optional[Follower]:
        follower = self.session.query(Follower).filter(Follower.bot == agent.name)
        follower.set_dbdriver(self)
        return follower.filter(Follower.chat == chat.id).first()

    def add_follower(self, agent: Agent, chat: Chat) -> Follower:
        follower = Follower(chat=chat.id, bot=agent.name)
        self.session.add(follower)
        self.session.commit()
        follower.set_dbdriver(self)
        return follower

    def delete_follower(self, agent: Agent, chat: Chat):

        follower = self.session.query(Follower).filter(and_(
            Follower.bot == agent.name,
            Follower.chat == chat.id,
        ))
        self.session.delete(follower)
        self.session.commit()
