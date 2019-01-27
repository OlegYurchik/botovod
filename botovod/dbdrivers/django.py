from botovod import Chat, dbdrivers
from botovod.extensions.djangoapp.botovod import models
import json
from json import JSONDecodeError
import logging


class DBDriver(dbdrivers.DBDriver):
    @classmethod
    def connect(cls, **settings):
        pass
    
    @classmethod
    def get_follower(cls, agent, chat):
        try:
            obj = models.Follower.objects.get(bot__name=agent.name, chat=chat.id)
        except models.Follower.DoesNotExist:
            return None
        return Follower(obj)
    
    @classmethod
    def add_follower(cls, agent, chat):
        bot = models.Bot.objects.get(name=agent.name)
        obj = models.Follower(
            chat=chat.id,
            bot=bot,
        )
        obj.save()
        return Follower(obj)
    
    @classmethod
    def delete_follower(cls, agent, chat):
        follower = models.Follower.objects.get(agent=agent.__class__.__name__, chat=chat.id)
        follower.delete()


class Follower(dbdrivers.Follower):
    def __init__(self, obj):
        self.obj = obj

    def get_chat(self):
        return Chat(self.obj.bot.agent, self.obj.chat)

    def get_dialog_name(self):
        return self.obj.dialog

    def set_dialog_name(self, name):
        self.obj.dialog = name
        self.obj.save()

    def get_next_step(self):
        return self.obj.next_step

    def set_next_step(self, next_step):
        self.obj.next_step = next_step
        self.obj.save()

    def get_history(self, after_date=None, before_date=None, input=None, text=None):
        messages = models.Message.objects.filter(follower=self.obj)
        if not after_date is None:
            messages = messages.filter(date__gt=after_date)
        if not before_date is None:
            messages = messages.filter(date__lt=before_date)
        if not input is None:
            messages = messages.filter(input=input)
        if not text is None:
            messages = messages.filter(text__iregex=text)
        return [message.to_object() for message in messages]

    def add_history(self, message, input=True):
        message = models.Message(
            follower = self.obj,
            input = input,
            text = message.text,
            images = json.loads([models.attachment_render(image) for image in message.images]),
            audios = json.loads([models.attachment_render(audio) for audio in message.audios]),
            videos = json.loads([models.attachment_render(video) for video in message.videos]),
            documents = json.loads([
                models.attachment_render(document) for document in message.documents
            ]),
            locations = json.loads([
                models.location_render(location) for location in message.locations
            ]),
            raw = json.loads(message.raw),
            date = message.date,
        )
        message.save()

    def clear_history(self, after_date=None, before_date=None, input=None, text=None):
        messages = models.Message.objects.filter(follower=self.obj)
        if not after_date is None:
            messages = messages.filter(date__gt=after_date)
        if not before_date is None:
            messages = messages.filter(date__lt=before_date)
        if not input is None:
            messages = messages.filter(input=input)
        messages.delete()

    def get_value(self, name):
        try:
            return json.loads(self.obj.data)[name]
        except KeyError:
            logging.warning("Value '%s' doesn't exist for follower %s %s", name,
                            self.obj.bot.agent, self.obj.chat)
        except JSONDecodeError:
            logging.error("Cannot get value '%s' for follower %s %s - incorrect json",
                          name, self.obj.bot.agent, self.obj.chat)

    def set_value(self, name, value):
        try:
            data = json.loads(self.obj.data)
        except JSONDecodeError:
            logging.error("Incorrect json structure for follower %s %s",
                            self.obj.bot.agent, self.obj.chat)
            data = dict()
        data[name] = value
        self.obj.data = json.dumps(data)
        self.obj.save()

    def delete_value(self, name):
        data = json.loads(self.obj.data)
        try:
            del data[name]
        except KeyError:
            logging.warning("Cannot delete value '%s' for follower %s %s - doesn't exist",
                            name, self.obj.bot.agent, self.obj.chat)
        self.obj.data = json.dumps(data)
        self.obj.save()
