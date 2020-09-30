from __future__ import annotations
from typing import Iterator, Optional


class Entity:
    def __init__(self, **raw):
        self.raw = dict(filter(lambda item: item[1] is not None, raw.items()))

    def __getattr__(self, item):
        return self.raw.get(item)


class Chat(Entity):
    def __init__(self, agent, id: str, **raw):
        super().__init__(**raw)
        self.agent = agent
        self.id = id


class Message(Entity):
    def __init__(self, text: Optional[str] = None, images: Iterator[Attachment] = (),
                 audios: Iterator[Attachment] = (), videos: Iterator[Attachment] = (),
                 documents: Iterator[Attachment] = (), locations: Iterator[Location] = (), **raw):
        super().__init__(**raw)
        self.text = text
        self.images = images
        self.audios = audios
        self.videos = videos
        self.documents = documents
        self.locations = locations


class Attachment(Entity):
    def __init__(self, url: Optional[str] = None, filepath: Optional[str] = None, **raw):
        super().__init__(**raw)
        self.url = url
        self.filepath = filepath


class Location(Entity):
    def __init__(self, latitude: float, longitude: float, **raw):
        super().__init__(**raw)
        self.latitude = latitude
        self.longitude = longitude


class Keyboard(Entity):
    def __init__(self, buttons: Iterator[Iterator[KeyboardButton]], **raw):
        super().__init__(**raw)
        self.buttons = buttons


class KeyboardButton(Entity):
    def __init__(self, text: str, **raw):
        super().__init__(**raw)
        self.text = text
