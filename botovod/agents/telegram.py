import botovod
from botovod import utils
import json
import requests
from threading import Thread
import time



class Agent(botovod.Agent):
    url = "https://api.telegram.org/bot%s/%s"

    def __init__(self, manager, name, token, method="polling", polling_delay=5,
                 polling_daemon=False, webhook_url=None, certificate_path=None):
        super().__init__(manager, name)
        self.token = token
        self.last_update = 0
        self.method = method

        self.polling_delay = polling_delay
        self.polling_daemon = polling_daemon
        self.polling_thread = None
        self.polling_run = False

        self.webhook_url = webhook_url
        self.certificate_path = certificate_path

    def start(self):
        if self.method == "polling":
            url = self.url % (self.token, "setWebhook")
            requests.get(url)
            self.polling_run = True
            if self.polling_thread and self.polling_thread.is_alive():
                self.polling_thread.join()
            self.polling_thread = Thread(target=self.polling_listener, daemon=self.polling_daemon)
            self.polling_thread.start()
        elif self.method == "webhook":
            self.polling_run = False
            if self.polling_thread and self.polling_thread.is_alive():
                self.polling_thread.join()
            self.set_webhook()
        self.running = True

    def stop(self):
        if self.method == "polling":
            self.polling_run = False
            self.polling_thread.join()
            self.polling_thread = None
        self.running = False

    def parser(self, status: int, headers: dict, body: str):
        update = json.loads(body)
        messages = dict()
        if update["update_id"] <= self.last_update:
            return messages
        self.last_update = update["update_id"]
        if "message" in update:
            message_data = update["message"]
            chat_data = message_data["chat"]

            chat = Chat(chat_data["id"])
            chat.custom = chat_data
            message = Message()
            message.parse(self, message_data)
            messages[chat] = message
        return messages

    def responser(self):
        return 200, dict(), ""

    def polling_listener(self):
        url = self.url % (self.token, "getUpdates")
        while self.polling_run:
            if self.last_update:
                response = requests.get(url, data={"offset": self.last_update + 1})
            else:
                response = requests.get(url)
            messages = dict()
            try:
                updates = json.loads(response.text)["result"]
            except:
                continue
            for update in updates:
                m = self.parser(response.status_code, response.headers, json.dumps(update))
                messages.update(m)
            for chat, message in messages.items():
                for handler in self.manager.handlers:
                    try:
                        handler(self, chat, message)
                    except utils.NotPassed as e:
                        continue
                    break
            time.sleep(self.polling_delay)

    def set_webhook(self):
        url = self.url % (self.token, "setWebhook")
        data = dict()
        files = dict()
        if not self.webhook_url is None:
            data["url"] = self.webhook_url
        if not self.certificate_path is None:
            files["certificate"] = open(self.certificate_path)
        response = requests.get(url, data=data, files=files)

    def send_message(self, chat, message):
        if not message.text is None:
            url = self.url % (self.token, "sendMessage")
            data = {"chat_id": chat.id, "text": message.text}
            if not message.keyboard is None:
                data["reply_markup"] = '{"keyboard":[%s],"resize_keyboard":true}' % ",".join([json.dumps([button]) for button in message.keyboard.buttons])
            data.update(**message.raw)
            requests.post(url, data=data)
        for image in message.images:
            self.send_photo(chat, image)
        for audio in  message.audios:
            self.send_audio(chat, audio)
        for document in message.documents:
            self.send_document(chat, document)
        for video in message.videos:
            self.send_video(chat, video)
        for location in message.locations:
            self.send_locations(chat, location)

    def send_photo(self, chat, image):
        url = self.url % (self.token, "sendPhoto")
        data = {"chat_id": chat.id}
        if "file_id" in image.raw:
            data["photo"] = image.raw["file_id"]
            response = requests.post(url, data=data)
        elif not image.url is None:
            data["photo"] = image.url
            response = requests.post(url, data=data)
        elif not image.file_path is None:
            with open(image.file_path) as f:
                response = requests.post(url, data=data, files={"photo": f})

    def send_audio(self, chat, audio):
        url = self.url % (self.token, "sendAudio")
        data = {"chat_id": chat.id}
        if "file_id" in audio.raw:
            data["audio"] = audio.raw["file_id"]
            response = requests.post(url, data=data)
        elif not audio.url is None:
            data["audio"] = audio.url
            response = requests.post(url, data=data)
        elif not audio.file_path is None:
            with open(audio.file_path) as f:
                response = requests.post(url, data=data, files={"audio": f})

    def send_document(self, chat, document):
        url = self.url % (self.token, "sendDocument")
        data = {"chat_id": chat.id}
        if "file_id" in document.raw:
            data["document"] = document.raw["file_id"]
            response = requests.post(url, data=data)
        elif not document.url is None:
            data["document"] = document.url
            response = requests.post(url, data=data)
        elif not document.file_path is None:
            with open(document.file_path) as f:
                response = requests.post(url, data=data, files={"document": f})

    def send_video(self, chat, video):
        url = self.url % (self.token, "sendVideo")
        data = {"chat_id": chat.id}
        if "file_id" in video.raw:
            data["video"] = video.raw["file_id"]
            response = requests.post(url, data=data)
        elif not video.url is None:
            data["video"] = video.url
            response = requests.post(url, data=data)
        elif not video.file_path is None:
            with open(video.file_path) as f:
                response = requests.post(url, data=data, files={"video": f})

    def send_location(self, chat, location, **args):
        url = self.url % (self.token, "sendLocation")
        data = {"chat_id": chat.id, "longitude": location.longitude, "latitude": location.latitude}
        data.update(**args)
        response = requests.post(url, data=data)

    def get_file(self, file_id):
        url = self.url % (self.token, "getFile")
        response = requests.get(url, data = {"file_id": file_id})
        return json.loads(response.text)
    """
    def get_me(self):
        pass

    def forward_message(self, to_chat, from_chat, message):
        pass

    def send_sticker(self, chat, sticker, **data):
        url = self.url % (self.token, "sendSticker")
        data = {"chat_id": chat.id}
        data.extend(**args)
        if hasattr(sticker, "id") and not sticker.id is None:
            data["sticker"] = sticker.id
            response = requests.post(url, data=data)
        elif not sticker.url is None:
            data["sticker"] = sticker.url
            response = requests.post(url, data=data)
        elif not sticker.file_path is None:
            with open(sticker.file_path) as f:
                response = requests.post(url, data=data, files={"sticker": f})
    
    def send_voice(self, chat, audio, **args):
        url = self.url % (self.token, "sendVoice")
        data = {"chat_id": chat.id}
        data.extend(**args)
        if hasattr(audio, "id") and not audio.id is None:
            data["voice"] = audio.id
            response = requests.post(url, data=data)
        elif not audio.url is None:
            data["voice"] = audio.url
            response = requests.post(url, data=data)
        elif not audio.file_path is None:
            with open(audio.file_path) as f:
                response = requests.post(url, data=data, files={"voice": f})
    
    def send_venue(self, chat, location, title, address, **args):
        url = self.url % (self.token, "sendLocation")
        data = {"chat_id": chat.id, "longitude": location.longitude, "latitude": location.latitude,
                "title": title, "address": address}
        data.extend(**args)
        response = requests.post(url, data=data)

    def send_contact(self, chat, attachment):
        pass
    
    def send_chat_action(self, chat, action):
        pass

    def get_user_profile_photo(self, user_id):
        pass
    
    def get_file(self, file_id):
        url = self.url % (self.token, "getFile")
        response = requests.get(url, data = {"file_id": file_id})
        return response.text

    def kick_chat_member(self, chat, user_id):
        pass
    
    def unban_chat_member(self, chat, user_id):
        pass
    
    def answer_callback_query(self, callback_query):
        pass

    def edit_message_text(self, message, text):
        pass
    
    def edit_message_caption(self, message, text):
        pass
    
    def edit_message_reply_markup(self):
        pass
    """
    

class Chat(botovod.Chat):
    def __init__(self, id):
        super().__init__("botovod.agents.telegram", id)


class Message(botovod.Message):
    def parse(self, agent, data):
        self.text = data.get("text", None)
        for photo_data in data.get("photo", []):
            photo = PhotoSize()
            photo.parse(agent, photo_data)
            self.images.append(photo)
        if "audio" in data:
            audio = Audio()
            audio.parse(agent, data["audio"])
            self.audios.append(audio)
        if "video" in data:
            video = Video()
            video.parse(agent, data["video"])
            self.videos.append(video)
        if "document" in data:
            document = Document()
            document.parse(agent, data["document"])
            self.documents.append(document)
        if "location" in data:
            location = Location(data["location"]["longitude"], data["location"]["latitude"])
            location.parse(data["location"])
            self.locations.append(location)
        self.raw = data


class Audio(botovod.Attachment):
    def parse(self, agent, data):
        response = agent.get_file(data["file_id"])["result"]["file_path"]
        self.url = agent.url % (agent.token, response)
        self.raw = data


class Document(botovod.Attachment):
    def parse(self, agent, data):
        response = agent.get_file(data["file_id"])["result"]["file_path"]
        self.url = agent.url % (agent.token, response)
        self.raw = data


class PhotoSize(botovod.Attachment):
    def parse(self, agent, data):
        response = agent.get_file(data["file_id"])["result"]["file_path"]
        self.url = agent.url % (agent.token, response)
        self.raw = data


class Video(botovod.Attachment):
    def parse(self, agent, data):
        response = agent.get_file(data["file_id"])["result"]["file_path"]
        self.url = agent.url % (agent.token, response)
        self.raw = data


class Location(botovod.Location):
    def parse(self, agent, data):
        self.longitude = data["longitude"]
        self.latitude = data["latitiude"]
        self.raw = data
