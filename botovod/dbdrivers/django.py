from botovod import dbdrivers
from botovod.extensions.djangoapp import models


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


class Follower(dbdrivers.Follower, models.Follower):
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
