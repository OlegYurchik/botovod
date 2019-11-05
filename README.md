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

Contents

=================

* [Release Notes](#release-notes)
  * [0.1.4](#version-0-1-4)
  * [0.1.5](#version-0-1-5)
  * [0.1.6](#version-0-1-6)
  * [0.1.7](#version-0-1-7)
  * [0.1.8](#version-0-1-8)
* [Getting Started](#getting-started)
  * [Installation from Pip](#installation-from-pip)
  * [Installation from GitHub](#installation-from-github)
  * [Quick Start](#quick-start)
* [User Guide](#user-guide)
  * [What is Botovod](#what-is-botovod)
  * [What is Agent](#what-is-agent)
* [Handlers](#handlers)
* [Examples](#examples)
* [Help the author](#help-the-author)
  * [Contribute repo](#contribute-repo)
  * [Donate](#donate)

## Release Notes

### Version 0.1.4

* Add new dbdriver - Gino
* Fix bugs

### Version 0.1.5

* Add new methods for telegram Agent
* Add emoji

### Version 0.1.6

* Fix gino getting follower
* Adding item assignments for Botovod objects

### Version 0.1.7

* Add new features for telegram agent
* Add start_dialog and start_async_dialog functions
* Fix gino driver bugs

### Version 0.1.8

* Fix utils handlers
* Add new methods for telegram
* Optimize interaction with DB

### Version 0.1.9

* Change Botovod API
* Fix telegram agent
* Remove old info from README.md

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
from botovod.agents import TelegramAgent


def echo(agent, chat, messsage, follower=None):
    agent.send_message(chat, text=message.text)


botovod = Botovod()
botovod.add_handler("echo", echo)

telegram_agent = TelegramAgent(token="your-telegram-token", method="polling)
botovod.add_agent("telegram", telegram_agent)

botovod.start()
```

This code setup and run Telegram echo-bot by polling

```python3
from botovod import Botovod
from botovod.agents import TelegramAgent
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


DBDriver.connect(engine="sqlite", database="file.db")
botovod = Botovod(DBDriver)

botovod.add_handler("RegisterDialog", RegisterDialog)

telegram_agent = TelegramAgent(token="your-telegram-token")
botovod.add_agent("telegram", telegram_agent)

botovod.start()
```

This code setup and run telegram code which working with database and followers
