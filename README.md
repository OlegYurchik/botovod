# botovod
[![MIT license](https://img.shields.io/badge/license-MIT-blue.svg)](
https://github.com/OlegYurchik/botovod/blob/master/LICENSE)
[![built with Python3](https://img.shields.io/badge/built%20with-Python3-red.svg)](
https://www.python.org/)
[![paypal](https://img.shields.io/badge/-PayPal-blue.svg)](
https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=QEZ85BDKJCM4E)
## Description
This is a simple and easy-to-use library for interacting with the Instagram. The library works
through the web interface of the Instagram and does not depend on the official API

User Guide
=================
* [Getting Started](#getting-started)
  * [Installation from Pip][#installation-from-pip]
  * [Installation from GitHub](#installation-from-github)
  * [Quick Start](#quick-start)
* [Documentation](#documentation)
  * [botovod](#botovod)
    * [botovod.Botovod](#botovod-botovod)
    * [botovod.dialogs](#botovod-dialogs)
      * [botovod.dialogs.Dialog](#botovod-dialogs-dialog)
    * [botovod.agents](#botovod-agents)
      * [botovod.agents.Agent](#botovod-agents-agent)
      * [botovod.agents.Entity](#botovod-agents-entity)
      * [botovod.agents.Chat](#botovod-agents-chat)
      * [botovod.agents.Message](#botovod-agents-message)
* [Handlers](#handlers)
* [Examples](#examples)
* [Help the author](#help-the-author)
  * [Contribute repo](#contribute-repo)
  * [Donate](#donate)
## Getting Started
### Installation from Pip
For installation botovod library from pip you should have pip with python (prefer python3.6 or
later)
```bash
pip install botovod
```
### Installation from GitHub
To basic installation from GitHub repository you should have git, python3 (prefer python3.6 or
later), pip (optionally) in your system
```bash
git clone https://github.com/OlegYurchik/botovod.git
cd botovod
pip install .
```
or
```bash
git clone https://github.com/OlegYurchik/botovod.git
cd botovod
python setup.py install
```
### Quick Start
After installation, you can use the library in your code. Below is a sneak example of using the
library
```python3
from botovod import Botovod
from botovod.agents.telegram import TelegramAgent


def echo(agent, chat, messsage):
    agent.send_message(chat, text=message.text)


botovod = Botovod()
botovod.handlers.append(echo)

telegram_agent = TelegramAgent(token="your-telegram-token", method="polling)
botovod.agents["telegram"] = telegram_agent

botovod.start()
```
This code setup and run Telegram echo-bot by polling
```python3
from botovod import Botovod
from botovod.agents.telegram import TelegramAgent
from botovod.dbdrivers.sqlalchemy import DBDriver
from botovod.dialogs import Dialog


class RegisterDialog(Dialog):
    def start(self):
        self.reply(text="Hello, my friend!")
        self.reply(text="What is your name?")
        self.set_next_step(self.what_name)

    def what_name(self):
        name = self.message.text
        self.follower.set_value("name", name)
        self.reply(text="Nice to meet you, %s. What would you want?" % name)
        self.set_next_step(self.menu)

    def menu(self):
        pass
        # your code


botovod = Botovod(DBDriver(engine="sqlite", database="file.mdb"))
botovod.handlers.append(RegisterDialog)

telegram_agent = TelegramAgent(token="your-telegram-token")
botovod.agents["telegram"] = telegram_agent

botovod.start()
```
This code setup and run telegram code which working with database and followers
## Documentation
### botovod
**package botovod**
### botovod.AgentDict
**class botovod.AgentDict**
#### Attributes
* botovod: botovod.Botovod

Botovod object
#### Methods
* \_\_init\_\_(self, botovod: botovod.Botovod)

Constructor for AgentDict
* \_\_setitem\_\_(self, key: str, value: botovod.agents.Agent)

Setting agents like a dict

* \_\_delitem\_\_(self, key: str)

Deleting agents like a dict
### botovod.Botovod
**class botovod.Botovod**
#### Attributes
* dbdriver: botovod.dbdrivers.DBDriver or None

Driver for working with database (for save data about followers and dialogs)
* agents: botovod.AgentDict

Dictionary for bots agents
* handlers: list

List with message and event handlers
* logger: logging.Logger
Logger
#### Methods
* \_\_init\_\_(self, dbdriver: (DBDriver, None)=None, logger:
logging.Logger=logging.getLogger(__name__))

This method initial botovod object
* start(self)

Starting all agents in botovod
* a_start(self)

Coroutine. Starting all agents in botovod
* stop(self)

Stopping all agents in botovod
* a_stop(self)

Coroutine. Stopping all agents in botovod
* listen(selfname: str, headers: dict, body: string) -> (int, dict, str) or None

Method, providing for webservers for listening requests from messengers servers and handle it.
* a_listen(self, name: str, headers: dict, body: string) -> (int, dict, str} or None

Coroutine, providing for webservers for listening requests from messengers servers and handle it.
### botovod.dialogs
**module botovod.dialogs**
### botovod.dialogs.Dialog
**class botovod.dialogs.Dialog**
#### Attributes
* agent: botovod.agents.Agent

Agent which get message
* chat: botovod.agents.Chat

Chat
* message: botovod.agents.Message

Message
* follower: botovod.dbdrivers.Folower

Follower
#### Methods
* \_\_init\_\_(self, agent: botovod.agents.Agent, chat: botovod.agents.Chat, message:
botovod.agents.Message)

Constructor for creating dialog object
* \_\_new\_\_(self, agent: botovod.agents.Agent, chat: botovod.agents.Chat, message:
botovod.agents.Message)

Method for handling request
* reply(self, text: str or None=None, images: Iterator of botovod.agents.Image=[],
audios: Iterator of botovod.agents.Audio=[], documents: Iterator of botovod.agents.Document=[],
videos: Iterator of botovod.agents.Video=[], locations: Iterator of botovod.agents.Location=[],
keyboard: botovod.agents.Keyboard or None=None, raw=None)

Method for replying to message
* a_reply(self, text: str or None=None, images: Iterator of botovod.agents.Image=[],
audios: Iterator of botovod.agents.Audio=[], documents: Iterator of botovod.agents.Document=[],
videos: Iterator of botovod.agents.Video=[], locations: Iterator of botovod.agents.Location=[],
keyboard: botovod.agents.Keyboard or None=None, raw=None)

Corotuine for replying to message
* set_next_step(self, function: Callable)

Method for setting next function for handling message in dialog
* a_set_next_step(self, function: Callable)

Coroutine for setting next function for handling message in dialog
* start(self)

Abstract method or coroutine for handling first message from request
### botovod.agents
**package botovod.agents**
### botovod.agents.Agent
**class botovod.agent.Agent**
#### Attributes
* botovod: botovod.Botovod

Botovod object
* name: str

Agent name in botovod
* running: bool

Varibale which True if agent is running else False
* logger: logging.Logger

Logger
#### Methods
* \_\_init\_\_(self, logger: logging.Logger=logging.getLogger(__name__)):

Agent constructor
* \_\_repr\_\_(self) -> str

Returning name of class
* listen(self, headers: dict, body: string) -> (int, dict, str) or None:

Method for getting requests from agent messenger and handle it
* a_listen(self, headers: dict, body: string) -> (int, dict, str) or None:

Coroutine for getting requests from agent messenger and handler it
* start(self):

Abstract method for run agent
* a_start(self):

Abstract coroutine for run agent
* stop(self):

Abstract method for stop agent
* a_stop(self):

Abstract coroutine for stop agent
* parser(self, headers: dict, body: str) -> list[tuple(Chat, Message))

Abstract method for parsing request and return list[tuple(Chat, Message))
* a_parser(self, headers: dict, body: str) -> list[tuple(Chat, Message)]

Abstract coroutine for parsing request and return list[tuple(Chat, Message)]
* responser(self, headers: dict, body: str) -> (int, dict, str)

Abstract method who return tuple with info for response to messenger
* a_responser(self, headers: dict, body: str) -> (int, dict, str)

Abstract coroutine who return tuple with info for response to messenger
* send_message(self, chat: botovod.agents.Chat, text: str or None=None, images: Iterator of
botovod.agents.Image=[], audios: Iterator of botovod.agents.Audio]=[], documents: Iterator of
botovod.agents.Document=[], videos: Iterator of botovod.agents.Video=[], locations: Iterator of
botovod.agents.Location=[], keyboard: botovod.agents.Keyboard or None=None, raw: dict or None=None)

Abstract method for sending message
* a_send_message(self, chat: botovod.agents.Chat, text: str or None=None, images: Iterator of
botovod.agents.Image=[], audios: Iterator of botovod.agents.Audio]=[], documents: Iterator of
botovod.agents.Document=[], videos: Iterator of botovod.agents.Video=[], locations: Iterator of
botovod.agents.Location=[], keyboard: botovod.agents.Keyboard or None=None, raw: dict or None=None)

Abstract coroutine for sending message
### botovod.agents.Entity
**class botovod.agents.Entity**
#### Attributes
* raw: dict

Dictonary with additional information
#### Methods
* \_\_init\_\_(self)

Constructor for Entity
### botovod.agents.Chat
**class botovod.agents.Chat(botovod.agents.Entity)**
#### Attributes
* agent: botovod.agents.Agent

Agent for this Chat
* id: str

Chat ID for this messenger
#### Nethods
* \_\_init\_\_(self, agent: botovod.agents.Agent, id: str)

Chat constructor
### botovod.agents.Message
**class botovod.agents.Message(botovod.agents.Entity)**
#### Attributes
=================
# **NOT UPDATED INFORMATION**
## Message

class botovod.Message

* __init__()

Message constructor, create fields:
- text - Message text
- images - List of images
- audios - List of audios
- videos - List of videos
- documents - List of documents
- locations - List of locations

## Attachment

class botovod.Attachment

Fields:
- url - Url for getting file
- file_path - File in local disk

Classes Image, Audio, Video and Document is a subclass of Attchment and has no extensions

## Agents

## Telegram


