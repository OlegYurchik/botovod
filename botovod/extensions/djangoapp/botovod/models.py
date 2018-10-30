from botovod import agents, Attachment, dbdrivers, Location, Message as BotoMessage
from django.core.exceptions import ValidationError
from django.db import models
import json
from json import JSONDecodeError


def meta_validator(value):
    try:
        json.loads(value)
    except JSONDecodeError:
        raise ValidationError("Value is not json")


class Bot(models.Model):
    name = models.CharField(max_length=255, blank=True, unique=True)
    agent = models.CharField(max_length=255, blank=True, choices=(agents.agent_list.items()))
    settings = models.TextField(blank=True, default="{}", validators=[meta_validator])


class Follower(models.Model):
    chat = models.CharField(max_length=255, blank=True)
    bot = models.ForeignKey(Bot, blank=True, on_delete=models.CASCADE)
    dialog = models.CharField(max_length=255, null=True)
    next_step = models.CharField(max_length=255, null=True)
    data = models.TextField(blank=True, default="{}", validators=[meta_validator])

    class Meta:
        unique_together = ("chat", "bot")


class Message(models.Model):
    follower = models.ForeignKey(Follower, blank=True, on_delete=models.CASCADE)
    input = models.BooleanField(blank=True)
    text = models.TextField(null=True)
    images = models.TextField(blank=True, default="[]", validators=[meta_validator])
    audios = models.TextField(blank=True, default="[]", validators=[meta_validator])
    videos = models.TextField(blank=True, default="[]", validators=[meta_validator])
    documents = models.TextField(blank=True, default="[]", validators=[meta_validator])
    locations = models.TextField(blank=True, default="[]", validators=[meta_validator])
    raw = models.TextField(null=True, validators=[meta_validator])
    date = models.DateTimeField(blank=True)

    def to_object(self):
        message = BotoMessage()
        message.text = self.text
        message.images = [attachment_parser(image) for image in json.loads(self.images)]
        message.audios = [attachment_parser(audio) for audio in json.loads(self.audios)]
        message.videos = [attachment_parser(video) for video in json.loads(self.videos)]
        message.documents = [attachment_parser(document) for document in json.loads(self.documents)]
        message.locations = [location_parser(location) for location in json.loads(self.locations)]
        message.raw = json.loads(self.raw)
        return message


def attachment_render(attachment):
    return {
        "url": attachment.url,
        "file": attachment.file,
        "raw": attachment.raw,
    }


def attachment_parser(data):
    attachment = Attachment
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
