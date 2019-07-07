from botovod.agents import Agent, Chat, Message
from botovod.utils.exceptions import NotPassed
import json
import logging
import requests
from threading import Thread
import time


class VkAgent(Agent):
    CALLBACK = "callback"
    BOT_POLLING = "bot_polling"
    USER_POLLING = "user_polling"

    api_url = "https://api.vk.com/method"
    bot_url = "{server}?act=a_check&key={key}&ts={ts}&wait={wait}"
    user_url = "https://{server}?act=a_check&key={key}&ts={ts}&wait={wait}&mode={mode}&version={version}"

    def __init__(self, token: str, group_id: int, api_version: str="5.50", method: str=CALLBACK,
                 confirm_key: (str, None)=None, secret_key: (str, None)=None, wait: int=25,
                 delay: int=5, daemon: bool=False,
                 logger: logging.Logger=logging.getLogger(__name__)):
        super().__init__()
        self.token = token
        self.group_id = group_id
        self.api_version = api_version
        self.method = method

        self.confirm_key = confirm_key
        self.secret_key = secret_key

        self.wait = wait
        self.delay = delay
        self.daemon = daemon
        
        self.key = None
        self.server = None
        self.ts = None
        self.thread = None

    def start(self):
        self.logger.info("[%s:%s] Starting agent...", self, self.name)

        self.running = True

        if self.method == self.BOT_POLLING:
            self.polling_auth()

            if self.thread and self.thread.is_alive():
                self.thread.join()
            self.thread = Thread(target=self.polling_listener, daemon=self.daemon)
            self.thread.start()
            self.logger.info("[%s:%s] Started by bot polling.", self, self.name)
        elif self.method == self.USER_POLLING:
            pass
        elif self.method == self.CALLBACK:
            pass

    def stop(self):
        self.logger.info("[%s:%s] Stopping agent...", self, self.name)

        if self.method in (self.BOT_POLLING, self.USER_POLLING):
            self.thread.join()
            self.thread = None
        self.running = False

        self.logger.info("[%s:%s] Agent stopped.", self, self.name)

    def parser(self, status: int, headers: dict, body):
        messages = []
        if body["type"] == "message_new":
            data = body["object"]
            chat = VkChat(data["from_id"])
            message = VkMessage()
            message.parse(data)
            messages.append([chat, message])
        return messages

    def responser(self, status: int, headers: dict, body: str):
        return 200, dict(), "ok"

    def send_message(self, chat, message):
        params = {"user_id": chat.id}
        if not message.text is None:
            params["message"] = message.text
        if not message.keyboard is None:
            buttons = [json.dumps([{"action": {"type": "text", "label": button.text}, "color": "default"}], ensure_ascii=False) for button in message.keyboard.buttons]
            buttons = ",".join(buttons)
            params["keyboard"] = '{"one_time":true,"buttons":[%s]}' % buttons
            params["keyboard"] = params["keyboard"]
        response = self.api_method(name="messages.send", params=params)

    def polling_listener(self):
        while self.running:
            url = self.bot_url.format(server=self.polling_server, key=self.key, ts=self.ts,
                                      wait=self.wait)
            messages = list()
            try:
                response = requests.get(url)
                data = response.json()
            except:
                time.sleep(self.delay)
                logging.error("[%s] Cannot update. Code: %s. Response: %s", self.name,
                              response.status_code, response.text)
                continue
            
            updates = data.get("updates", None)
            failed = data.get("failed", None)
            if not failed is None:
                logging.warning("[%s] Get incorrect update. Code: %s. Response: %s", self.name,
                                response.status_code, response.text)
                if 2 <= failed <= 3:
                    self.polling_auth()
                time.sleep(self.delay)
                continue
            self.polling_ts = data["ts"]
            
            for update in updates:
                ms = self.parser(response.status_code, response.headers, update)
                messages.extend(ms)
            for chat, message in messages:
                for handler in self.botovod.handlers:
                    try:
                        handler(self, chat, message)
                    except NotPassed:
                        continue
                    break
            time.sleep(self.delay)

    def polling_auth(self):
        response = self.api_method(name="groups.getLongPollServer", params={"group_id": self.group_id})
        try:
            data = response.json()["response"]
            logging.info("[%s] Success auth. Code: %s. Response: %s", self.name, response.status_code,
                         response.text)
        except KeyError:
            logging.error("[%s] Incorrect auth response. Code: %s. Response: %s", self.name,
                          response.status_code, response.text)
        
        self.polling_key = data["key"]
        self.polling_server = data["server"]
        self.polling_ts = data["ts"]

    def api_method(self, name, params={}, method="get"):
        params["v"] = self.api_version
        params["access_token"] = self.token
        if method.lower() == "get":
            url = f"{self.api_url}/{name}?" + "&".join([f"{key}={value}" for key, value in params.items()]) 
            return requests.get(url)


class VkChat(Chat):
    def __init__(self, id):
        super().__init__("botovod.agents.vk", id)


class VkMessage(Message):
    def parse(self, data):
        self.text = data["text"]
        self.raw = data
