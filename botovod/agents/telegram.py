from botovod import utils
from botovod.agents import Agent, Attachment, Chat, Location, Message
import json
import logging
import requests
from threading import Thread
import time


class TelegramAgent(Agent):
    WEBHOOK = "webhook"
    POLLING = "polling"

    url = "https://api.telegram.org/bot{token}/{method}"

    def __init__(self, token, method: str=POLLING, delay: int=5, daemon: bool=False,
                 webhook_url: (str, None)=None, certificate_path: (str, None)=None,
                 logger: logging.Logger=logging.getLogger(__name__)):
        super().__init__(logger)
        self.token = token
        self.method = method

        if method == self.POLLING:
            self.delay = delay
            self.daemon = daemon
            self.thread = None
        elif webhook_url is None:
            raise ValueError("Need set webhook_url")
        else:
            self.webhook_url = webhook_url
            self.certificate_path = certificate_path

        self.last_update = 0

    def start(self):
        self.logger.info("[%s:%s] Starting agent...", self, self.name)

        self.set_webhook()
        self.running = True

        if self.method == self.POLLING:
            if self.thread and self.thread.is_alive():
                self.thread.join()
            self.thread = Thread(target=self.polling_listener, daemon=self.daemon)
            self.thread.start()
            self.logger.info("[%s:%s] Started by polling.", self, self.name)
        elif self.method == self.WEBHOOK:
            self.logger.info("[%s:%s] Started by webhook.", self, self.name)

    def stop(self):
        self.logger.info("[%s:%s] Stopping agent...", self, self.name)

        if self.method == self.POLLING:
            self.thread.join()
            self.thread = None
        self.running = False

        self.logger.info("[%s:%s] Agent stopped.", self, self.name)

    def parser(self, headers: dict, body: str):
        update = json.loads(body)
        messages = []
        if update["update_id"] <= self.last_update:
            return messages
        self.last_update = update["update_id"]
        if "message" in update:
            message_data = update["message"]
            chat_data = message_data["chat"]

            chat = TelegramChat(chat_data["id"])
            chat.custom = chat_data
            message = TelegramMessage()
            message.parse(self, message_data)
            messages.append([chat, message])
        return messages

    def responser(self, status: int, headers: dict, body: str):
        return 200, {}, ""

    def polling_listener(self):
        url = self.url.format(token=self.token, method="getUpdates")
        while self.running:
            try:
                params = {"offset": self.last_update + 1} if self.last_update > 0 else {}
                response = requests.get(url, params=params)
                updates = response.json()["result"]
            except:
                self.logger.error("[%s:%s] Get incorrect update! Code: %s. Response: %s", self,
                                  self.name, response.status_code, response.text)
                time.sleep(self.delay)
                continue
            for update in updates:
                self.listen(response.headers, json.dumps(update))
            time.sleep(self.delay)

    def set_webhook(self):
        self.logger.info("[%s:%s] Setting webhook...", self, self.name)

        url = self.url.format(token=self.token, method="setWebhook")
        data, files = {}, {}
        if self.method == self.WEBHOOK:
            data["url"] = self.webhook_url
            if self.certificate_path is not None:
                files["certificate"] = open(self.certificate_path)
        response = requests.get(url, data=data, files=files)
        if response.status_code != 200:
            self.logger.error("[%s:%s] Webhook doesn't set! Code: %s; Body: %s", self, self.name,
                              response.status_code, response.text)
            return

        self.logger.info("[%s:%s] Set webhook.", self, self.name)

    def send_message(self, chat, message):
        if not message.text is None:
            url = self.url.format(token=self.token, method="sendMessage")
            data = {"chat_id": chat.id, "text": message.text}
            # if not message.keyboard is None:
            #     data["reply_markup"] = '{"keyboard":[%s],"resize_keyboard":true}' % ",".join([json.dumps([button.text]) for button in message.keyboard.buttons])
            data.update(**message.raw)
            response = requests.post(url, data=data)
            if response.status_code != 200:
                self.logger.error("[%s:%s] Cannot send message! Code: %s; Body: %s", self,
                                  self.name, response.status_code, response.text)
        for image in message.images:
            self.send_photo(chat, image)
        for audio in  message.audios:
            self.send_audio(chat, audio)
        for document in message.documents:
            self.send_document(chat, document)
        for video in message.videos:
            self.send_video(chat, video)
        for location in message.locations:
            self.send_location(chat, location)

    def send_photo(self, chat, image):
        url = self.url.format(token=self.token, method="sendPhoto")
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
        else:
            return
        if response.status_code != 200:
            self.logger.error("[%s:%s] Cannot send photo! Code: %s; Body: %s", self, self.name,
                              response.status_code, response.text)

    def send_audio(self, chat, audio):
        url = self.url.format(token=self.token, method="sendAudio")
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
        else:
            return
        if response.status_code != 200:
            self.logger.error("[%s:%s] Cannot send audio! Code: %s; Body: %s", self, self.name,
                              response.status_code, response.text)

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
        else:
            return
        if response.status_code != 200:
            self.logger.error("[%s:%s] Cannot send document! Code: %s; Body: %s", self, self.name,
                              response.status_code, response.text)

    def send_video(self, chat, video):
        url = self.url.format(token=self.token, method="sendVideo")
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
        else:
            return
        if response.status_code != 200:
            self.logger.error("[%s:%s] Cannot send video! Code: %s; Body: %s", self, self.name,
                              response.status_code, response.text)

    def send_location(self, chat, location, **args):
        url = self.url.format(token=self.token, method="sendLocation")
        data = {"chat_id": chat.id, "longitude": location.longitude, "latitude": location.latitude}
        data.update(**args)
        response = requests.post(url, data=data)
        if response.status_code != 200:
            self.logger.error("[%s:%s] Cannot send location! Code: %s; Body: %s", self, self.name,
                              response.status_code, response.text)

    def get_file(self, file_id):
        url = self.url.format(token=self.token, method="getFile")
        response = requests.get(url, data = {"file_id": file_id})
        if response.status_code != 200:
            self.logger.error("[%s:%s] Cannot get file! Code: %s; Body: %s", self, self.name,
                              response.status_code, response.text)
        return response.json()
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
    

class TelegramChat(Chat):
    def __init__(self, id):
        super().__init__("botovod.agents.telegram", id)


class TelegramMessage(Message):
    def parse(self, agent, data):
        self.text = data.get("text", None)
        for photo_data in data.get("photo", []):
            photo = TelegramPhotoSize()
            photo.parse(agent, photo_data)
            self.images.append(photo)
        if "audio" in data:
            audio = TelegramAudio()
            audio.parse(agent, data["audio"])
            self.audios.append(audio)
        if "video" in data:
            video = TelegramVideo()
            video.parse(agent, data["video"])
            self.videos.append(video)
        if "document" in data:
            document = TelegramDocument()
            document.parse(agent, data["document"])
            self.documents.append(document)
        if "location" in data:
            location = TelegramLocation(data["location"]["longitude"], data["location"]["latitude"])
            location.parse(agent, data["location"])
            self.locations.append(location)
        self.raw = data


class TelegramAudio(Attachment):
    def parse(self, agent, data):
        response = agent.get_file(data["file_id"])["result"]["file_path"]
        self.url = agent.url % (agent.token, response)
        self.raw = data


class TelegramDocument(Attachment):
    def parse(self, agent, data):
        response = agent.get_file(data["file_id"])["result"]["file_path"]
        self.url = agent.url % (agent.token, response)
        self.raw = data


class TelegramPhotoSize(Attachment):
    def parse(self, agent, data):
        response = agent.get_file(data["file_id"])["result"]["file_path"]
        self.url = agent.url % (agent.token, response)
        self.raw = data


class TelegramVideo(Attachment):
    def parse(self, agent, data):
        response = agent.get_file(data["file_id"])["result"]["file_path"]
        self.url = agent.url % (agent.token, response)
        self.raw = data


class TelegramLocation(Location):
    def parse(self, agent, data):
        self.longitude = data["longitude"]
        self.latitude = data["latitiude"]
        self.raw = data
