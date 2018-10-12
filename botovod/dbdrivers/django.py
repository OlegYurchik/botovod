from botovod import dbdrivers
from botovod.extensions.djangoapp import models


class DBDriver(dbdrivers.DBDriver):
    def connect(self, **settings):
        pass
    
    def get_follower(self, agent, chat):
        obj = models.Follower.objects.get(agent=agent.__class__.__name__, chat=chat.id)
        return Follower(obj)
    
    def add_follower(self, agent, chat):
        obj = models.Follower(
            chat=chat.id,
            agent=agent.__class__.__name__,
        )
        obj.save()
        return Follower(obj)
    
    def delete_follower(self, agent, chat):
        follower = Follower.objects.get(agent=agent.__class__.__name__, chat=chat.id)
        follower.delete()


class Follower(dbdrivers.Follower):
    def __init__(self, obj):
        self.obj = obj

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
            return json.dumps(self.obj.data)[name]
        except JSONDecodeError:
            return None
    
    def set_value(self, name, value):
        data = json.dumps(self.obj.data)
        data[name] = value
        self.obj.data = json.loads(data)
        self.obj.save()
    
    def delete_value(self, name):
        data = json.dumps(self.obj.data)
        try:
            del data[name]
        except KeyError:
            pass
        self.obj.data = json.loads(data)
        self.obj.save()
