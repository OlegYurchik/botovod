from botovod import dbdrivers, Message as BotoMessage, Image, Audio, Video, Document, Location
from django.db import models
import json
from json import JSONDecodeError


class DBDriver(dbdrivers.DBDriver):
    def connect(self, **settings):
        pass
    
    def get_follower(self, agent, chat):
        return Follower.objects.get(agent=agent.__class__.__name__, chat=chat.id)
    
    def add_follower(self, agent, chat):
        follower = Follower(
            chat=chat.id,
            agent=agent.__class__.__name__,
        )
        follower.save()
        return follower
    
    def delete_follower(self, agent, chat):
        follower = Follower.objects.get(agent=agent.__class__.__name__, chat=chat.id)
        follower.delete()


class Follower(models.Model, dbdrivers.Follower):
    chat = models.CharField(max_length=255, blank=True)
    agent = models.CharField(max_length=255, blank=True)
    next_step = models.CharField(max_length=255, null=True)
    data = models.TextField(blank=True, default="{}")

    class Meta:
        unique_together = ("chat", "agent")

    def get_next_step(self):
        return self.next_step
    
    def set_next_step(self, next_step):
        self.next_step = next_step
    
    def get_history(self, after_date=None, before_date=None, input=None, text=None):
        messages = Message.objects.filter(follower=self)
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
        message = Message(
            follower = self,
            input = input,
            text = message.text,
            images = json.loads([attachment_render(image) for image in message.images]),
            audios = json.loads([attachment_render(audio) for audio in message.audios]),
            videos = json.loads([attachment_render(video) for video in message.videos]),
            documents = json.loads([attachment_render(document) for document in message.documents]),
            locations = json.loads([location_render(location) for locations in message.locations]),
            raw = json.loads(message.raw),
            date = message.date,
        )
        message.save()
    
    def clear_history(self, after_date=None, before_date=None, input=None, text=None):
        messages = Message.objects.filter(follower=self)
        if not after_date is None:
            messages = messages.filter(date__gt=after_date)
        if not before_date is None:
            messages = messages.filter(date__lt=before_date)
        if not input is None:
            messages = messages.filter(input=input)
        messages.delete()
    
    def get_value(self, name):
        try:
            return json.dumps(self.data)[name]
        except JSONDecodeError:
            return None
    
    def set_value(self, name, value):
        data = json.dumps(self.data)
        data[name] = value
        self.data = json.loads(data)
        self.save()
    
    def delete_value(self, name):
        data = json.dumps(self.data)
        try:
            del data[name]
        except KeyError:
            pass
        self.data = json.loads(data)
        self.save()


class Message(models.Model):
    follower = models.ForeignKey(Follower, blank=True, on_delete=models.CASCADE)
    input = models.BooleanField(blank=True)
    text = models.TextField(null=True)
    images = models.TextField(blank=True, default="[]")
    audios = models.TextField(blank=True, default="[]")
    videos = models.TextField(blank=True, default="[]")
    documents = models.TextField(blank=True, default="[]")
    locations = models.TextField(blank=True, default="[]")
    raw = models.TextField(null=True)
    date = models.DateTimeField(blank=True)

    def to_object(self):
        message = BotoMessage()
        message.text = self.text
        message.images = [attachment_parser(Image, image) for image in json.loads(self.images)]
        message.audios = [attachment_parser(Audio, audio) for audio in json.loads(self.audios)]
        message.videos = [attachment_parser(Video, video) for video in json.loads(self.videos)]
        message.documents = [attachment_parser(Document, document) for docuemnt in json.loads(self.documents)]
        message.locations = [location_parser(location) for location in json.loads(self.locations)]
        message.raw = json.loads(self.raw)
        return message


def attachment_render(attachment):
    return {
        "url": attachment.url,
        "file": attachment.file,
        "raw": attachment.raw,
    }


def attachment_parser(cls, data):
    attachment = cls()
    attachment.url = data["url"]
    attachment.file = data["file"]
    attachment.raw = data["raw"]
    return attachment


def location_render(location):
    return {
        "longitude": location.longitude,
        "latitude": location.latitude,
        "raw": location.raw,
    }


def location_parser(data):
    location = Location(
        longitude = data["longitude"],
        latitude = data["latitude"],
    )
    location.raw = data["raw"]
    return location