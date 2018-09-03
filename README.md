# botovod
[![MIT license](https://img.shields.io/badge/license-MIT-blue.svg)](
https://github.com/OlegYurchik/botovod/blob/master/LICENSE)
[![built with Python3](https://img.shields.io/badge/built%20with-Python3-red.svg)](
https://www.python.org/)
[![paypal](https://img.shields.io/badge/-PayPal-blue.svg)](
https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=QEZ85BDKJCM4E)

### Description
This is a simple and easy-to-use library for interacting with the Instagram. The library works
through the web interface of the Instagram and does not depend on the official API

User Guide
=================

* [Getting Started](#getting-started)
  * [Basic Installation](#basic-installation)
  * [Installation via Virtualenv](#installation-via-virtualenv)
* [Quick Start](#quick-start)
* [Objects](#objects)
  * [Botovod](#botovod)
  * [Agent](#agent)
  * [Chat](#chat)
  * [Message](#message)
  * [Attachment](#attachment)
  * [Location](#location)
* [Agents](#agents)
  * [Telegram](#telegram)
* [Handlers](#handlers)
* [Examples](#examples)
* [Help the author](#help-the-author)
  * [Contribute repo](#contribute-repo)
  * [Donate](#donate)

## Getting Started

## Basic Installation

To basic installation you should have git, python3 (prefer python3.6 or later), pip (optionally) in
your system

```bash
1. git clone https://github.com/OlegYurchik/botovod.git
2. cd botovod
3. pip install .
or
3. python setup.py install
```  

## Installation via Virtualenv

To installation via Virtualenv, you should have git, python3 (prefer python3.6 or later), pip
(optionally) and virtualenv in your system

```bash
1. git clone https://github.com/OlegYurchik/botovod.git
2. cd botovod
3. source venv/bin/activate
4. pip install .
or
4. python setup.py install
5. deactivate
```

## Quick Start

After installation, you can use the library in your code. Below is a sneak example of using the
library

```python3
from botovod import Botovod, Message

def handler(agent, messsage):
    agent.send_message(event)

settings = [
    {"name": "telegram", "agent": "botovod.agents.telegram", 
     "settings": {"token": "your-telegram-token", "method": "polling"}},
]
botovod = Botovod(settings)
botovod.add_handler(handler)
botovod.start("telegram")
```

This code setup and run Telegram echo-bot by polling

## Objects

## Botovod

class botovod.Botovod

* __init__(settings: dict)

This method get settings about bots for creating it

* add_handler(handler: function)

Add new handler to botovod

* start(name=None: string)

If name not is None - start bot with this name else start all bots

* stop(name=None: string)

If name not is None - stop bot with this name else stop all bots
        
* listen(name: string, headers: dict, body: string): {"status": int, "headers": dict, "body": string}

Method for getting requests from messangers and handle it

## Agent

class botovod.Agent

* __init__(manager: Botovod, name: string):

Agent constructor

* listen(headers: dict, body: string):

Method for getting requests from agent messanger and handle it 

* start():

Abstract method for run bot
    
* stop():

Abstract method for stop bot
    
* parser(status: int, headers: dict, body: string): dict(Chat=Message)

Abstract method for parsing request and return dict(Chat=Message)
    
* responser(): dict("status": int, "headers": dict, "body": string)

Abstract method who return dict with info for response to messanger

* send_message(chat: Chat, message: Message)

Abstract method for sending message

## Chat

class botovod.Chat

* __init__(agent_cls: class, id: int)

Chat constructor

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


