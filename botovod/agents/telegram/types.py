from __future__ import annotations
from datetime import datetime
import json
from typing import Iterator, Optional, Union

from botovod.agents.types import Attachment, Chat, Keyboard, KeyboardButton, Location, Message


class TelegramUser(Chat):
    def __init__(self, agent, id: int, is_bot: bool, first_name: str,
                 last_name: Optional[str] = None, username: Optional[str] = None,
                 language: Optional[str] = None):

        super().__init__(agent=agent, id=str(id), is_bot=is_bot, first_name=first_name,
                         last_name=last_name, username=username, language=language)

    @classmethod
    def parse(cls, agent, data: dict):
        return cls(
            agent=agent,
            id=data["id"],
            is_bot=data["is_bot"],
            first_name=data["first_name"],
            last_name=data.get("last_name"),
            username=data.get("username"),
            language=data.get("language_code"),
        )

    def render(self):
        data = {"id": self.id, "is_bot": self.raw["is_bot"], "first_name": self.raw["first_name"]}
        if self.raw.get("last_name") is not None:
            data["last_name"] = self.raw["last_name"]
        if self.raw.get("username") is not None:
            data["username"] = self.raw["username"]
        if self.raw.get("language") is not None:
            data["language_code"] = self.raw["language"]
        return data


class TelegramChat(Chat):
    def __init__(self, agent, id: int, type: str, title: Optional[str] = None,
                 username: Optional[str] = None, first_name: Optional[str] = None,
                 last_name: Optional[str] = None, photo: Optional[dict] = None,
                 description: Optional[str] = None, invite_link: Optional[str] = None,
                 pinned_message: Optional[dict] = None, permissions: Optional[dict] = None,
                 sticker_set: Optional[str] = None, can_set_sticker: Optional[bool] = None):
        super().__init__(agent=agent, id=str(id), type=type, title=title, username=username,
                         first_name=first_name, last_name=last_name, photo=photo,
                         description=description, invite_link=invite_link,
                         pinned_message=pinned_message, permissions=permissions,
                         sticker_set=sticker_set, can_set_sticker=can_set_sticker)

    @classmethod
    def parse(cls, agent, data: dict):
        return cls(
            agent=agent,
            id=data["id"],
            type=data["type"],
            title=data.get("title"),
            username=data.get("username"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            photo=data.get("photo"),
            description=data.get("description"),
            invite_link=data.get("invite_link"),
            pinned_message=data.get("pinned_message"),
            permissions=data.get("permissions"),
            sticker_set=data.get("sticker_set_name"),
            can_set_sticker=data.get("can_set_sticker_set"),
        )

    def render(self):
        data = {"id": self.id, "type": self.raw["type"]}
        if self.raw.get("title") is not None:
            data["title"] = self.raw["title"]
        if self.raw.get("username") is not None:
            data["username"] = self.raw["username"]
        if self.raw.get("first_name") is not None:
            data["first_name"] = self.raw["first_name"]
        if self.raw.get("last_name") is not None:
            data["last_name"] = self.raw["last_name"]
        if self.raw.get("photo") is not None:
            data["photo"] = self.raw["photo"]
        if self.raw.get("description") is not None:
            data["description"] = self.raw["description"]
        if self.raw.get("invite_link") is not None:
            data["invite_link"] = self.raw["invite_link"]
        if self.raw.get("pinned_message") is not None:
            data["pinned_message"] = self.raw["pinned_message"]
        if self.raw.get("permissions") is not None:
            data["permissions"] = self.raw["permissions"]
        if self.raw.get("sticker_set") is not None:
            data["sticker_set_name"] = self.raw["sticker_set"]
        if self.raw.get("can_sticker_set") is not None:
            data["can_set_sticker_set"] = self.raw["can_set_sticker"]
        return data

    @property
    def pinned_message(self) -> Optional[TelegramMessage]:
        if self.raw.get("pinned_message") is not None:
            return TelegramMessage.parse(data=self.raw["pinned_message"])


# Нужны остальные необязательные поля
class TelegramMessage(Message):
    def __init__(self, id: int, datetime: int, chat: dict, text: Optional[str] = None,
                 images: Iterator[Attachment] = (), audios: Iterator[Attachment] = (),
                 videos: Iterator[Attachment] = (), documents: Iterator[Attachment] = (),
                 locations: Iterator[Location] = (), **raw):
        super().__init__(id=id, datetime=datetime, chat=chat, text=text, images=images,
                         audios=audios, videos=videos, documents=documents, locations=locations,
                         **raw)

    @classmethod
    def parse(cls, data: dict, agent=None):
        images = []
        audios = []
        videos = []
        documents = []
        locations = []
        if "photo" in data:
            images.append(TelegramAttachment.parse(data=data["photo"][-1], agent=agent))
        if "audio" in data:
            audios.append(TelegramAttachment.parse(data=data["audio"], agent=agent))
        if "video" in data:
            videos.append(TelegramAttachment.parse(data=data["video"], agent=agent))
        if "document" in data:
            documents.append(TelegramAttachment.parse(data=data["document"], agent=agent))
        if "location" in data:
            locations.append(TelegramLocation.parse(data=data["location"]))
        raw = {"contact": data.get("contact")}
        return cls(
            id=data["message_id"],
            datetime=data["date"],
            chat=data.get("chat"),
            text=data.get("text"),
            images=images,
            audios=audios,
            videos=videos,
            documents=documents,
            locations=locations,
            **raw,
        )

    @classmethod
    async def a_parse(cls, data: dict, agent=None):
        images = []
        audios = []
        videos = []
        documents = []
        locations = []
        if "photo" in data:
            images.append(await TelegramAttachment.a_parse(data=data["photo"][-1], agent=agent))
        if "audio" in data:
            audios.append(await TelegramAttachment.a_parse(data=data["audio"], agent=agent))
        if "video" in data:
            videos.append(await TelegramAttachment.a_parse(data=data["video"], agent=agent))
        if "document" in data:
            documents.append(await TelegramAttachment.a_parse(data=data["document"], agent=agent))
        if "location" in data:
            locations.append(TelegramLocation.parse(data=data["location"]))
        raw = {"contact": data.get("contact")}
        return cls(
            id=data["message_id"],
            datetime=data["date"],
            chat=data["chat"],
            text=data.get("text"),
            images=images,
            audios=audios,
            videos=videos,
            documents=documents,
            locations=locations,
            **raw,
        )

    def render(self):
        data = {
            "message_id": self.raw["id"],
            "date": self.raw["datetime"],
            "chat": self.raw["chat"],
        }
        if self.text is not None:
            data["text"] = self.text
        return data

    @property
    def datetime(self) -> datetime:
        return datetime.utcfromtimestamp(self.raw["datetime"])

    @property
    def chat(self) -> Chat:
        return TelegramChat.parse(agent=None, data=self.raw["chat"])

    @property
    def contact(self):
        if "contact" in self.raw:
            return TelegramContact.parse(self.raw["contact"])


class TelegramCallback(Message):
    def __init__(self, id: str, user: dict, message: Optional[dict] = None,
                 inline_message_id: Optional[str] = None, chat_instance: Optional[str] = None,
                 data: Optional[str] = None, game_short_name: Optional[str] = None):
        super().__init__(id=id, text=data, user=user, message=message,
                         inline_message_id=inline_message_id, chat_instance=chat_instance,
                         game_short_name=game_short_name)

    @classmethod
    def parse(cls, data: dict):
        return cls(
            id=data["id"],
            user=data["from"],
            message=data.get("message"),
            inline_message_id=data.get("inline_message_id"),
            chat_instance=data.get("chat_instance"),
            data=data.get("data"),
            game_short_name=data.get("game_short_name"),
        )

    def render(self):
        data = {"id": self.raw["id"], "from": self.raw["user"]}
        if self.raw.get("message") is not None:
            data["message"] = self.raw["message"]
        if self.raw.get("inline_message_id") is not None:
            data["inline_message_id"] = self.raw["inline_message_id"]
        if self.raw.get("chat_instance") is not None:
            data["chat_instance"] = self.raw["chat_instance"]
        if self.raw.get("data") is not None:
            data["data"] = self.raw["data"]
        if self.raw.get("game_short_name") is not None:
            data["game_short_name"] = self.raw["game_short_name"]

    @property
    def message(self) -> Optional[TelegramMessage]:
        if self.raw.get("message") is not None:
            return TelegramMessage.parse(data=self.raw["message"])


class TelegramAttachment(Attachment):
    def __init__(self, url: Optional[str] = None, filepath: Optional[str] = None,
                 id: Optional[str] = None, size: Optional[int] = None):
        super().__init__(url=url, filepath=filepath, id=id, size=size)

    @classmethod
    def parse(cls, data: dict, agent=None):
        if "file_path" in data and agent is not None:
            url = agent.requester.FILE_URL.format(token=agent.token, path=data["file_path"])
        elif agent is not None:
            return agent.get_file(data["file_id"])
        else:
            url = None

        return cls(id=data["file_id"], url=url, size=data.get("file_size"))

    @classmethod
    async def a_parse(cls, data: dict, agent=None):
        if "file_path" in data and agent is not None:
            url = agent.requester.FILE_URL.format(token=agent.token, path=data["file_path"])
        elif agent is not None:
            return await agent.a_get_file(data["file_id"])
        else:
            url = None

        return cls(id=data["file_id"], url=url, size=data.get("file_size"))

    def render(self):
        if self.raw.get("id") is not None:
            return self.raw["id"]
        elif self.url is not None:
            return self.url
        elif self.filepath is not None:
            return open(self.filepath, "rb")

    async def a_render(self):
        if self.raw.get("id") is not None:
            return self.raw["id"]
        elif self.url is not None:
            return self.url
        elif self.filepath is not None:
            return open(self.filepath, "rb")


class TelegramLocation(Location):
    def __init__(self, latitude: float, longitude: float):
        super().__init__(latitude=latitude, longitude=longitude)

    @classmethod
    def parse(cls, data: dict):
        return cls(latitude=data["latitude"], longitude=data["longitude"])

    def render(self):
        return {"latitude": self.latitude, "longitude": self.longitude}


class TelegramContact:
    def __init__(self, phone: str, first_name: str, last_name: Optional[str] = None,
                 user_id: Optional[int] = None, vcard: Optional[str] = None):
        self.phone = phone
        self.first_name = first_name
        self.last_name = last_name
        self.user_id = user_id
        self.vcard = vcard

    @classmethod
    def parse(cls, data):
        return cls(
            phone=data["phone_number"],
            first_name=data["first_name"],
            last_name=data.get("last_name"),
            user_id=data.get("user_id"),
            vcard=data.get("vcard"),
        )

    def render(self):
        data = {"phone_number": self.phone, "first_name": self.first_name}
        if self.last_name is not None:
            data["last_name"] = self.last_name
        if self.user_id is not None:
            data["user_id"] = self.user_id
        if self.vcard is not None:
            data["vcard"] = self.vcard
        return data


class TelegramVenue(Location):
    def __init__(self, latitude: float, longitude: float):
        super().__init__(latitude=latitude, longitude=longitude)

    @classmethod
    def parse(cls, data: dict):
        return cls(latitude=data["latitude"], longitude=data["longitude"])


class TelegramKeyboard(Keyboard):
    def __init__(self, buttons: Iterator[Iterator[Union[KeyboardButton, str]]],
                 resize: bool = False, one_time: bool = False, selective: bool = False):
        super().__init__(buttons=buttons, resize=resize, one_time=one_time, selective=selective)

    def render(self):
        data = {
            "keyboard": [],
            "resize_keyboard": self.raw["resize"],
            "one_time_keyboard": self.raw["one_time"],
            "selective": self.raw["selective"],
        }
        for line in self.buttons:
            line_data = []
            data["keyboard"].append(line_data)
            for button in line:
                if isinstance(button, str):
                    line_data.append(button)
                elif hasattr(button, "render"):
                    line_data.append(button.render())
                else:
                    line_data.append(button.text)
        return json.dumps(data)

    @staticmethod
    def default_render(keyboard: Keyboard):
        data = {"keyboard": []}
        for line in keyboard.buttons:
            line_data = []
            data["keyboard"].append(line_data)
            for button in line:
                line_data.append(button.text)
        return json.dumps(data)


class TelegramInlineKeyboard(Keyboard):
    def __init__(self, buttons: Iterator[Iterator[TelegramInlineKeyboardButton]]):
        super().__init__(buttons=buttons)

    def render(self):
        data = {"inline_keyboard": []}
        for line in self.buttons:
            line_data = []
            data["inline_keyboard"].append(line_data)
            for button in line:
                line_data.append(button.render())
        return json.dumps(data)


class TelegramKeyboardButton(KeyboardButton):
    def __init__(self, text: str, contact: bool = False, location: bool = False):
        super().__init__(text=text, contact=contact, location=location)

    def render(self):
        return {
            "text": self.text,
            "request_contact": self.raw["contact"],
            "request_location": self.raw["location"],
        }


class TelegramInlineKeyboardButton(KeyboardButton):
    def __init__(self, text: str, url: Optional[str] = None, data: Optional[str] = None,
                 inline_query: Optional[str] = None, inline_chat: Optional[str] = None,
                 game: Optional[dict] = None):
        super().__init__(text=text, url=url, data=data, inline_query=inline_query,
                         inline_chat=inline_chat, game=game)

    def render(self):
        data = {"text": self.text}
        if self.raw.get("url") is not None:
            data["url"] = self.raw["url"]
        if self.raw.get("data") is not None:
            data["callback_data"] = self.raw["data"]
        if self.raw.get("inline_query") is not None:
            data["switch_inline_query"] = self.raw["inline_query"]
        if self.raw.get("inline_chat") is not None:
            data["switch_inline_query_current_chat"] = self.raw["inline_chat"]
        if self.raw.get("game") is not None:
            data["callback_game"] = self.raw["game"]
        return data
